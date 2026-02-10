"""
Pytest 全局配置和 Fixtures
"""
import asyncio
import pytest
from typing import AsyncGenerator

from config import settings
from utils import APIClient
from utils.cleanup import cleaner


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api_client() -> AsyncGenerator[APIClient, None]:
    """创建全局API客户端"""
    async with APIClient(
        base_url=settings.full_url,
        timeout=settings.request_timeout
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[APIClient, None]:
    """创建测试用API客户端（每个测试函数独立）"""
    async with APIClient(
        base_url=settings.full_url,
        timeout=settings.request_timeout
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_settings():
    """测试配置"""
    return settings


@pytest.fixture(scope="session")
def data_cleaner():
    """数据清理器"""
    return cleaner


@pytest.fixture(scope="session", autouse=True)
async def prepare_test_environment():
    """准备测试环境（在所有测试之前执行）"""
    print("\n" + "="*60)
    print("🔧 准备测试环境...")
    print("="*60)
    
    # 1. 检查并准备管理员账号
    try:
        from app.db.session import async_session
        from app.models.admin import Admin
        from app.core.security import get_password_hash
        from sqlalchemy import select
        
        async with async_session() as db:
            # 查询管理员账号
            result = await db.execute(
                select(Admin).where(Admin.username == "admin")
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                # 重置密码并解锁
                admin.password_hash = get_password_hash("admin123")
                admin.failed_login_attempts = 0
                admin.locked_until = None
                admin.is_active = True
                print("✅ 管理员账号已重置并解锁")
            else:
                # 创建管理员账号
                admin = Admin(
                    username="admin",
                    email="admin@example.com",
                    password_hash=get_password_hash("admin123"),
                    is_super_admin=True,
                    is_active=True,
                    failed_login_attempts=0,
                    locked_until=None
                )
                db.add(admin)
                print("✅ 管理员账号已创建")
            
            await db.commit()
            print(f"   用户名: admin")
            print(f"   密码: admin123")
    except Exception as e:
        print(f"⚠️  管理员账号准备失败: {e}")
        print("   测试将继续，但管理员相关测试可能失败")
    
    # 2. 检查 LLM 配置
    if settings.has_llm_config:
        print(f"✅ LLM 已配置: {settings.llm_provider}")
    else:
        print(f"⚠️  LLM 未配置 ({settings.llm_provider})")
        print(f"   涉及AI功能的测试可能超时")
        print(f"   请设置 {settings.llm_provider.upper()}_API_KEY 环境变量")
    
    print("="*60)
    print("🚀 测试环境准备完成，开始执行测试...")
    print("="*60 + "\n")
    
    yield


@pytest.fixture(scope="session", autouse=True)
async def cleanup_after_all_tests(data_cleaner, api_client):
    """所有测试结束后清理数据"""
    yield
    
    # 测试结束后清理
    if settings.cleanup_after_test:
        await data_cleaner.cleanup_all(api_client)


def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    # 为集成测试添加标记
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
