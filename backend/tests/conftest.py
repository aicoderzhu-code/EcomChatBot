"""
测试配置和 Fixtures
"""
import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from db import get_db
from db.session import Base

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# 创建测试会话工厂
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


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
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


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
        "description": "测试描述",
        "url": "https://example.com/webhook",
        "event_type": "conversation.created",
        "timeout": 30,
        "retry_count": 3,
        "retry_interval": 60,
    }
