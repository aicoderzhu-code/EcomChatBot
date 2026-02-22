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
    
    print(f"✅ 使用管理员账号: {settings.admin_username}")
    print(f"✅ API 基础URL: {settings.base_url}")
    print(f"✅ LLM 提供商: {settings.llm_provider}")
    
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
    
    print("\n" + "="*60)
    print("🏁 所有测试执行完毕")
    print("="*60)


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
            item.add_marker(pytest.mark.slow)
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        # AI 对话、RAG 生成、LLM 相关测试标记为 slow（每次调用 LLM 需 10-30 秒）
        if "test_ai_chat" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
        if "test_rag" in str(item.fspath) and "test_rag_generate" in item.name:
            item.add_marker(pytest.mark.slow)
        if "test_intent" in str(item.fspath) and "test_extract_entities" in item.name:
            item.add_marker(pytest.mark.slow)
