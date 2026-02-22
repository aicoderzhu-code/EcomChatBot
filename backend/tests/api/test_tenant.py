"""
租户管理测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin
from config import settings


@pytest.mark.tenant
class TestTenant(BaseAPITest, TenantTestMixin):
    """租户管理测试"""

    @pytest.mark.asyncio
    async def test_register_tenant(self):
        """测试租户注册"""
        tenant_data = self.data_gen.generate_tenant(settings.tenant_prefix)

        response = await self.client.post(
            "/tenant/register",
            json=tenant_data
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "tenant_id" in data
        assert "api_key" in data
        assert "message" in data
        assert data["api_key"].startswith("eck_")

        # 注册清理
        self.cleaner.register_tenant(data["tenant_id"])

    @pytest.mark.asyncio
    async def test_register_with_invalid_email(self):
        """测试使用无效邮箱注册"""
        tenant_data = self.data_gen.generate_tenant()
        tenant_data["contact_email"] = "invalid-email"

        response = await self.client.post(
            "/tenant/register",
            json=tenant_data
        )

        # 应该返回422验证错误
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_with_weak_password(self):
        """测试使用弱密码注册"""
        tenant_data = self.data_gen.generate_tenant()
        tenant_data["password"] = "123"

        response = await self.client.post(
            "/tenant/register",
            json=tenant_data
        )

        # 应该返回400或422错误
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_login_tenant(self):
        """测试租户登录"""
        # 先注册
        tenant_info = await self.create_test_tenant()

        # 登录
        response = await self.client.post(
            "/tenant/login",
            json={
                "email": tenant_info["email"],
                "password": tenant_info["password"]
            }
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "tenant_id" in data
        assert data["token_type"] == "bearer"
        assert data["tenant_id"] == tenant_info["tenant_id"]

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self):
        """测试使用错误密码登录"""
        # 先注册
        tenant_info = await self.create_test_tenant()

        # 使用错误密码登录
        response = await self.client.post(
            "/tenant/login",
            json={
                "email": tenant_info["email"],
                "password": "WrongPassword123"
            }
        )

        # 应该返回401错误
        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_get_tenant_info_with_api_key(self):
        """测试使用API Key获取租户信息"""
        # 创建租户
        tenant_info = await self.create_test_tenant()

        # 设置API Key
        self.client.set_api_key(tenant_info["api_key"])

        # 获取租户信息
        response = await self.client.get("/tenant/info")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["tenant_id"] == tenant_info["tenant_id"]
        assert "company_name" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_tenant_info_with_jwt_token(self):
        """测试使用JWT Token获取租户信息"""
        # 创建租户并登录
        tenant_info = await self.create_test_tenant()
        jwt_token = await self.login_tenant(
            tenant_info["email"],
            tenant_info["password"]
        )

        # 设置JWT Token
        self.client.set_jwt_token(jwt_token)

        # 获取租户信息
        response = await self.client.get("/tenant/info-token")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["tenant_id"] == tenant_info["tenant_id"]
        assert "company_name" in data

    @pytest.mark.asyncio
    async def test_get_subscription_info(self):
        """测试获取订阅信息"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 获取订阅信息
        response = await self.client.get("/tenant/subscription")
        data = self.assert_success(response)

        # 验证返回数据
        assert "plan_type" in data
        assert "status" in data
        # 新注册的租户应该是免费套餐
        assert data["plan_type"] in ["free", "trial"]

    @pytest.mark.asyncio
    async def test_get_quota_usage(self):
        """测试获取配额使用情况"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 获取配额
        response = await self.client.get("/tenant/quota")
        data = self.assert_success(response)

        # 验证返回数据（API 返回按类型分组的配额信息）
        assert "conversation" in data
        assert "concurrent" in data
        assert "api_call" in data
        # 每种配额类型包含 used, limit, remaining, percentage
        assert "limit" in data["conversation"]
        assert "used" in data["conversation"]

    @pytest.mark.asyncio
    async def test_get_usage_statistics(self):
        """测试获取用量统计"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 获取当前月份的用量
        import datetime
        now = datetime.datetime.now()

        response = await self.client.get(
            "/tenant/usage",
            params={
                "year": now.year,
                "month": now.month
            }
        )

        data = self.assert_success(response)

        # 验证返回数据结构
        assert isinstance(data, dict)
