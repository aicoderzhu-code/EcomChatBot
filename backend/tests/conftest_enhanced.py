"""
增强的测试配置和 Fixtures
提供完整的测试基础设施支持
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from core import create_access_token, hash_password
from db import get_async_session, get_redis
from db.session import Base
from models import Admin, Subscription, Tenant
from models.admin import AdminRole, AdminStatus

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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


# ==================== 基础 Fixtures ====================


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
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
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=-1)
    return redis


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, redis_mock) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_redis():
        return redis_mock

    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ==================== 测试数据 Fixtures ====================


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
def conversation_data() -> Dict[str, Any]:
    """对话测试数据"""
    return {
        "user_id": f"user_{uuid.uuid4().hex[:8]}",
        "channel": "web",
        "metadata": {"source": "test", "device": "desktop"},
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
        "events": ["conversation.created", "conversation.closed"],
        "secret": "test_secret_key",
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
        role=AdminRole.SUPER_ADMIN,
        status=AdminStatus.ACTIVE,
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
        start_at=datetime.utcnow(),
        expire_at=datetime.utcnow() + timedelta(days=365),
    )
    db_session.add(subscription)

    await db_session.commit()
    await db_session.refresh(tenant)

    # 将API Key保存到tenant对象中以便测试使用
    tenant.plain_api_key = api_key

    return tenant


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
        start_at=datetime.utcnow(),
        expire_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(subscription)

    await db_session.commit()
    await db_session.refresh(tenant)

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


@pytest.fixture
def mock_milvus_service():
    """Mock Milvus向量数据库服务"""
    mock_service = MagicMock()
    mock_service.insert = AsyncMock(return_value={"ids": ["1", "2", "3"]})
    mock_service.search = AsyncMock(
        return_value=[
            {"id": "1", "score": 0.95, "entity": {"title": "知识1"}},
            {"id": "2", "score": 0.85, "entity": {"title": "知识2"}},
        ]
    )
    mock_service.delete = AsyncMock(return_value=True)
    return mock_service


# ==================== 工具函数 ====================


@pytest.fixture
def assert_response_success():
    """断言响应成功"""

    def _assert(response, expected_status=200):
        assert response.status_code == expected_status, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert data.get("success") is not False, f"Response not successful: {data}"
        return data

    return _assert


@pytest.fixture
def assert_response_error():
    """断言响应错误"""

    def _assert(response, expected_status=400):
        assert response.status_code == expected_status
        data = response.json()
        assert data.get("success") is False or "error" in data
        return data

    return _assert


@pytest.fixture
def generate_test_user_id():
    """生成测试用户ID"""

    def _generate():
        return f"user_{uuid.uuid4().hex[:8]}"

    return _generate


@pytest.fixture
def generate_test_email():
    """生成测试邮箱"""

    def _generate():
        return f"test_{uuid.uuid4().hex[:8]}@example.com"

    return _generate


# ==================== 批量测试数据生成 ====================


@pytest.fixture
def generate_multiple_tenants():
    """生成多个租户数据"""

    def _generate(count: int = 5):
        return [
            {
                "company_name": fake.company(),
                "contact_name": fake.name(),
                "contact_email": fake.email(),
                "contact_phone": fake.phone_number(),
                "password": "Test@123456",
            }
            for _ in range(count)
        ]

    return _generate


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


# ==================== 清理 Fixtures ====================


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """测试后自动清理"""
    yield
    # 清理操作（如果需要）
    pass
