"""
认证授权测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin


@pytest.mark.auth
class TestAuth(BaseAPITest, TenantTestMixin):
    """认证授权测试"""

    @pytest.mark.asyncio
    async def test_api_key_authentication_success(self):
        """测试API Key认证成功"""
        # 创建租户
        tenant_info = await self.create_test_tenant()

        # 设置API Key
        self.client.set_api_key(tenant_info["api_key"])

        # 访问需要认证的接口
        response = await self.client.get("/tenant/info")
        self.assert_success(response)

    @pytest.mark.asyncio
    async def test_api_key_authentication_failure(self):
        """测试API Key认证失败"""
        # 设置无效的API Key
        self.client.set_api_key("invalid_api_key_123456")

        # 访问需要认证的接口
        response = await self.client.get("/tenant/info")

        # 应该返回 400（格式无效）、401（未授权）或 403（禁止访问）错误
        assert response.status_code in [400, 401, 403]

    @pytest.mark.asyncio
    async def test_jwt_token_authentication_success(self):
        """测试JWT Token认证成功"""
        # 创建租户并登录
        tenant_info = await self.create_test_tenant()
        jwt_token = await self.login_tenant(
            tenant_info["email"],
            tenant_info["password"]
        )

        # 设置JWT Token
        self.client.set_jwt_token(jwt_token)

        # 访问需要认证的接口
        response = await self.client.get("/tenant/info-token")
        self.assert_success(response)

    @pytest.mark.asyncio
    async def test_jwt_token_authentication_failure(self):
        """测试JWT Token认证失败"""
        # 设置无效的JWT Token
        self.client.set_jwt_token("invalid.jwt.token")

        # 访问需要认证的接口
        response = await self.client.get("/tenant/info-token")

        # 应该返回401错误
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_no_authentication(self):
        """测试无认证访问受保护接口"""
        # 不设置任何认证信息
        self.client.clear_auth()

        # 访问需要认证的接口
        response = await self.client.get("/tenant/info")

        # 应该返回401错误
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_cross_tenant_access_prevention(self):
        """测试跨租户访问防护"""
        # 创建两个租户
        tenant1 = await self.create_test_tenant()
        tenant2 = await self.create_test_tenant()

        # 使用租户1的API Key
        self.client.set_api_key(tenant1["api_key"])

        # 获取租户1的信息（应该成功）
        response = await self.client.get("/tenant/info")
        data = self.assert_success(response)
        assert data["tenant_id"] == tenant1["tenant_id"]

        # 切换到租户2的API Key
        self.client.set_api_key(tenant2["api_key"])

        # 获取租户信息（应该返回租户2的信息，不是租户1的）
        response = await self.client.get("/tenant/info")
        data = self.assert_success(response)
        assert data["tenant_id"] == tenant2["tenant_id"]
        assert data["tenant_id"] != tenant1["tenant_id"]
