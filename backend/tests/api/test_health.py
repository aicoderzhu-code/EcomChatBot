"""
健康检查测试
"""
import pytest
from test_base import BaseAPITest


@pytest.mark.health
class TestHealth(BaseAPITest):
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """测试根路径"""
        # 根路径不在api/v1下，需要直接访问
        from config import settings
        base_url = settings.base_url

        import httpx
        # 设置 NO_PROXY 避免代理干扰
        async with httpx.AsyncClient(proxies={"all://": None}) as client:
            response = await client.get(f"{base_url}/")
            
        # 验证返回数据
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查接口"""
        response = await self.client.get("/health")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["status"] == "healthy"
        # 健康检查返回timestamp而不是version
        assert "timestamp" in data or "version" in data
