"""
测试配置和 Fixtures
"""
import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from core import create_access_token, hash_password
from db import get_db, get_redis
from db.session import Base
from models import Admin, Subscription, Tenant

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ==================== SQLite UUID 兼容性修复 ====================
# 问题：SQLAlchemy 在 SQLite 上编译 PostgreSQL UUID 类型时失败
# 解决方案：为 SQLite 方言注册 UUID 类型编译器，并确保在导入模型前执行

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String as SAString


# 为 SQLite 注册 PostgreSQL UUID 类型的编译器
# 当 SQLite 遇到 PG_UUID 类型时，将其编译为 VARCHAR(36)
# 注意：这必须在导入任何使用 PG_UUID 的模型之前执行
@compiles(PG_UUID, 'sqlite')
def compile_uuid_sqlite(element, compiler, **kw):
    """在 SQLite 上将 UUID 编译为 VARCHAR(36)"""
    return "VARCHAR(36)"


# 同时为 INET 类型注册编译器（用于 IP 地址字段）
from sqlalchemy.dialects.postgresql import INET as PG_INET


@compiles(PG_INET, 'sqlite')
def compile_inet_sqlite(element, compiler, **kw):
    """在 SQLite 上将 INET 编译为 VARCHAR(45)"""
    return "VARCHAR(45)"


# 修补 GUID 类型以确保在 SQLite 上工作
def _patch_guid_for_sqlite():
    """修补 GUID 类型以支持 SQLite"""
    try:
        from models.audit_log import GUID

        # 保存原始方法（仅在尚未修补时）
        if not hasattr(GUID, '_original_load_dialect_impl'):
            GUID._original_load_dialect_impl = GUID.load_dialect_impl

            def patched_load_dialect_impl(self, dialect):
                if dialect.name == 'sqlite':
                    return dialect.type_descriptor(SAString(36))
                return GUID._original_load_dialect_impl(self, dialect)

            GUID.load_dialect_impl = patched_load_dialect_impl

        # 同样修补 IPAddress 类型
        from models.audit_log import IPAddress
        if not hasattr(IPAddress, '_original_load_dialect_impl'):
            IPAddress._original_load_dialect_impl = IPAddress.load_dialect_impl

            def patched_ip_load_dialect_impl(self, dialect):
                if dialect.name == 'sqlite':
                    return dialect.type_descriptor(SAString(45))
                return IPAddress._original_load_dialect_impl(self, dialect)

            IPAddress.load_dialect_impl = patched_ip_load_dialect_impl

    except ImportError:
        pass


_patch_guid_for_sqlite()


# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# 创建测试会话工厂
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Faker实例
fake = Faker(["zh_CN"])


def _create_redis_mock() -> AsyncMock:
    """创建一个完整的 Redis mock 对象"""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.incr = AsyncMock(return_value=1)
    mock.incrby = AsyncMock(return_value=1)
    mock.decr = AsyncMock(return_value=0)
    mock.decrby = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=-1)
    mock.ping = AsyncMock(return_value=True)
    mock.close = AsyncMock(return_value=None)
    mock.hget = AsyncMock(return_value=None)
    mock.hset = AsyncMock(return_value=True)
    mock.hgetall = AsyncMock(return_value={})
    mock.lpush = AsyncMock(return_value=1)
    mock.rpush = AsyncMock(return_value=1)
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.zadd = AsyncMock(return_value=1)
    mock.zrem = AsyncMock(return_value=1)
    mock.zcard = AsyncMock(return_value=0)
    mock.zrange = AsyncMock(return_value=[])
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.pipeline = MagicMock()
    pipe_mock = AsyncMock()
    pipe_mock.execute = AsyncMock(return_value=[0, 0, 1, True])
    pipe_mock.set = MagicMock(return_value=pipe_mock)
    pipe_mock.zadd = MagicMock(return_value=pipe_mock)
    pipe_mock.zremrangebyscore = MagicMock(return_value=pipe_mock)
    pipe_mock.zcard = MagicMock(return_value=pipe_mock)
    pipe_mock.expire = MagicMock(return_value=pipe_mock)
    mock.pipeline.return_value = pipe_mock
    mock.info = AsyncMock(return_value={
        "connected_clients": 1,
        "used_memory_human": "1M",
        "uptime_in_days": 1,
        "total_commands_processed": 100,
    })
    return mock


def _create_sync_redis_mock() -> MagicMock:
    """创建一个同步 Redis mock（用于 api/security.py 的 RateLimiter）"""
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.set = MagicMock(return_value=True)
    mock.incr = MagicMock(return_value=1)
    mock.expire = MagicMock(return_value=True)
    mock.pipeline = MagicMock()
    pipe_mock = MagicMock()
    pipe_mock.set = MagicMock(return_value=pipe_mock)
    pipe_mock.execute = MagicMock(return_value=[True])
    mock.pipeline.return_value = pipe_mock
    return mock


# ==================== 基础 Fixtures ====================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    # 清理所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def redis_mock():
    """Mock Redis客户端"""
    return _create_redis_mock()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, redis_mock) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    import db.redis as redis_module

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis():
        return redis_mock

    # 1. FastAPI 依赖注入覆盖
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # 2. 模块级别 Redis 全局变量覆盖（覆盖直接调用 get_redis() 的代码）
    original_redis_client = redis_module.redis_client
    redis_module.redis_client = redis_mock

    # 3. 覆盖 api/security.py 中的同步 RateLimiter
    sync_redis_mock = _create_sync_redis_mock()
    with patch("api.security.rate_limiter.redis", sync_redis_mock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    # 清理
    redis_module.redis_client = original_redis_client
    app.dependency_overrides.clear()


# ==================== 测试数据 Fixtures ====================


@pytest.fixture
def test_tenant_data() -> dict[str, Any]:
    """测试租户数据"""
    return {
        "company_name": "测试公司",
        "contact_name": "张三",
        "contact_email": "test@example.com",
        "contact_phone": "13800138000",
        "password": "testpassword123",
    }


@pytest.fixture
def test_webhook_data() -> dict[str, Any]:
    """测试 Webhook 数据"""
    return {
        "name": "测试 Webhook",
        "endpoint_url": "https://example.com/webhook",
        "events": ["conversation.started"],  # 使用实际存在的事件类型
        "secret": None,  # 可选，不提供则自动生成
    }


@pytest.fixture
def admin_data() -> Dict[str, Any]:
    """管理员测试数据"""
    return {
        "username": "test_admin",
        "password": "Admin@123456",
        "email": fake.email(),
        "phone": fake.phone_number(),
        "role": "super_admin",
    }


@pytest.fixture
def tenant_data() -> Dict[str, Any]:
    """租户测试数据"""
    return {
        "company_name": fake.company(),
        "contact_name": fake.name(),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "password": "Tenant@123456",
    }


@pytest.fixture
def knowledge_data() -> Dict[str, Any]:
    """知识库测试数据"""
    return {
        "knowledge_type": "faq",
        "title": fake.sentence(),
        "content": fake.text(),
        "category": "常见问题",
        "tags": ["测试", "FAQ"],
        "source": "manual",
        "priority": 1,
    }


@pytest.fixture
def conversation_data() -> Dict[str, Any]:
    """对话测试数据"""
    return {
        "user_id": f"user_{uuid.uuid4().hex[:8]}",
        "channel": "web",
        "metadata": {"source": "test", "device": "desktop"},
    }


@pytest.fixture
def payment_data() -> Dict[str, Any]:
    """支付测试数据"""
    return {
        "plan_type": "basic",
        "duration_months": 1,
        "payment_type": "pc",
        "subscription_type": "new",
        "description": "测试订阅",
    }


@pytest.fixture
def webhook_data() -> Dict[str, Any]:
    """Webhook测试数据"""
    return {
        "name": "测试Webhook",
        "endpoint_url": "https://example.com/webhook",
        "events": ["conversation.started", "conversation.ended"],
        "secret": None,  # 可选，让服务自动生成
    }


@pytest.fixture
def model_config_data() -> Dict[str, Any]:
    """模型配置测试数据"""
    return {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "sk-test-key",
        "api_base": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": 2000,
        "use_case": "chat",
        "is_default": True,
    }


# ==================== 数据库实体 Fixtures ====================


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession, admin_data: Dict) -> Admin:
    """创建测试管理员"""
    admin = Admin(
        admin_id=f"ADMIN_{uuid.uuid4().hex[:12].upper()}",
        username=admin_data["username"],
        password_hash=hash_password(admin_data["password"]),
        email=admin_data["email"],
        phone=admin_data.get("phone"),
        role="super_admin",
        status="active",
        permissions=["*"],
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession, tenant_data: Dict) -> Tenant:
    """创建测试租户"""
    tenant_id = f"TENANT_{uuid.uuid4().hex[:12].upper()}"
    api_key = f"sk_live_{uuid.uuid4().hex}"

    tenant = Tenant(
        tenant_id=tenant_id,
        company_name=tenant_data["company_name"],
        contact_name=tenant_data["contact_name"],
        contact_email=tenant_data["contact_email"],
        contact_phone=tenant_data.get("contact_phone"),
        password_hash=hash_password(tenant_data["password"]),
        api_key_hash=hash_password(api_key),
        status="active",
    )
    db_session.add(tenant)

    # 创建订阅
    subscription = Subscription(
        tenant_id=tenant_id,
        plan_type="free",
        status="active",
        start_date=datetime.utcnow(),
        expire_at=datetime.utcnow() + timedelta(days=365),
        enabled_features='["BASIC_CHAT"]',
        conversation_quota=1000,
        concurrent_quota=10,
        storage_quota=1,
        api_quota=10000,
    )
    db_session.add(subscription)

    await db_session.commit()
    await db_session.refresh(tenant)

    # 将API Key保存到tenant对象中以便测试使用
    tenant.plain_api_key = api_key

    return tenant


# ==================== Token Fixtures ====================


@pytest.fixture
def admin_token(test_admin: Admin) -> str:
    """生成管理员Token"""
    return create_access_token(
        subject=test_admin.admin_id,
        role=test_admin.role,
        expires_delta=timedelta(hours=8),
    )


@pytest.fixture
def tenant_token(test_tenant: Tenant) -> str:
    """生成租户Token"""
    return create_access_token(
        subject=test_tenant.tenant_id,
        tenant_id=test_tenant.tenant_id,
        expires_delta=timedelta(hours=24),
    )


@pytest.fixture
def admin_headers(admin_token: str) -> Dict[str, str]:
    """管理员请求头"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def tenant_headers(tenant_token: str) -> Dict[str, str]:
    """租户Token请求头"""
    return {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def tenant_api_key_headers(test_tenant: Tenant) -> Dict[str, str]:
    """租户API Key请求头"""
    return {
        "X-API-Key": test_tenant.plain_api_key,
        "Content-Type": "application/json",
    }


# ==================== 扩展实体 Fixtures ====================


@pytest_asyncio.fixture
async def test_tenant_with_basic_plan(
    db_session: AsyncSession, tenant_data: Dict
) -> Tenant:
    """创建带基础套餐的测试租户"""
    tenant_id = f"TENANT_{uuid.uuid4().hex[:12].upper()}"
    api_key = f"sk_live_{uuid.uuid4().hex}"

    tenant = Tenant(
        tenant_id=tenant_id,
        company_name=tenant_data["company_name"],
        contact_name=tenant_data["contact_name"],
        contact_email=tenant_data["contact_email"],
        contact_phone=tenant_data.get("contact_phone"),
        password_hash=hash_password(tenant_data["password"]),
        api_key_hash=hash_password(api_key),
        status="active",
    )
    db_session.add(tenant)

    # 创建基础套餐订阅
    subscription = Subscription(
        tenant_id=tenant_id,
        plan_type="basic",
        status="active",
        start_date=datetime.utcnow(),
        expire_at=datetime.utcnow() + timedelta(days=30),
        enabled_features='["BASIC_CHAT", "KNOWLEDGE_BASE"]',
        conversation_quota=5000,
        concurrent_quota=20,
        storage_quota=5,
        api_quota=50000,
    )
    db_session.add(subscription)

    await db_session.commit()
    await db_session.refresh(tenant)

    tenant.plain_api_key = api_key

    return tenant


# ==================== 批量数据生成 Fixtures ====================


@pytest.fixture
def generate_multiple_knowledge():
    """生成多个知识库条目"""

    def _generate(count: int = 10):
        categories = ["常见问题", "产品说明", "使用指南", "售后服务", "政策条款"]
        return [
            {
                "knowledge_type": "faq",
                "title": fake.sentence(),
                "content": fake.text(),
                "category": fake.random_element(categories),
                "tags": [fake.word() for _ in range(3)],
                "source": "manual",
                "priority": fake.random_int(1, 5),
            }
            for _ in range(count)
        ]

    return _generate


# ==================== Mock服务 Fixtures ====================


@pytest.fixture
def mock_llm_service():
    """Mock LLM服务"""
    mock_service = MagicMock()
    mock_service.chat = AsyncMock(
        return_value={
            "response": "这是AI的回复",
            "model": "gpt-3.5-turbo",
            "input_tokens": 10,
            "output_tokens": 15,
            "total_tokens": 25,
        }
    )
    mock_service.classify_intent = AsyncMock(return_value="order_inquiry")
    mock_service.extract_entities = AsyncMock(
        return_value={"order_id": "123456", "product": "商品名"}
    )
    return mock_service


@pytest.fixture
def mock_rag_service():
    """Mock RAG服务"""
    mock_service = MagicMock()
    mock_service.retrieve = AsyncMock(
        return_value=[
            {
                "knowledge_id": "K001",
                "title": "测试知识",
                "content": "知识内容",
                "score": 0.95,
            }
        ]
    )
    mock_service.generate = AsyncMock(
        return_value={
            "answer": "基于知识库的回答",
            "sources": ["K001"],
        }
    )
    return mock_service


@pytest.fixture
def mock_payment_service():
    """Mock支付服务"""
    mock_service = MagicMock()
    mock_service.create_payment_order = AsyncMock(
        return_value=(
            MagicMock(
                order_number="ORDER_TEST_001",
                amount=99.00,
                currency="CNY",
                expired_at=datetime.utcnow() + timedelta(hours=2),
            ),
            "<form>支付表单HTML</form>",
        )
    )
    mock_service.verify_payment = AsyncMock(return_value=True)
    return mock_service
