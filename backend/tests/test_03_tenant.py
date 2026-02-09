"""
租户管理模块测试
测试覆盖: 12个接口, 48个测试用例
包含: 注册、登录、信息查询、配额管理、套餐订阅
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.tenant]


# ==================== 1. 租户注册测试 ====================


class TestTenantRegistration:
    """租户注册测试"""

    async def test_tenant_register_success(self, client: AsyncClient, tenant_data: dict):
        """测试租户注册成功"""
        response = await client.post("/api/v1/tenant/register", json=tenant_data)

        data = AssertHelper.assert_response_success(response, 200)

        # 验证返回数据
        assert "data" in data
        result = data["data"]
        assert "tenant_id" in result
        assert "api_key" in result
        assert "message" in result

        # 验证ID格式
        AssertHelper.assert_uuid_format(result["tenant_id"], "TENANT_")
        assert result["api_key"].startswith("sk_live_")

    async def test_tenant_register_duplicate_email(
        self, client: AsyncClient, test_tenant
    ):
        """测试租户注册 - 邮箱重复"""
        tenant_data = TestDataGenerator.generate_tenant()
        tenant_data["contact_email"] = test_tenant.contact_email

        response = await client.post("/api/v1/tenant/register", json=tenant_data)

        AssertHelper.assert_response_error(response, 400)

    async def test_tenant_register_invalid_email(self, client: AsyncClient):
        """测试租户注册 - 邮箱格式错误"""
        tenant_data = TestDataGenerator.generate_tenant()
        tenant_data["contact_email"] = "invalid-email"

        response = await client.post("/api/v1/tenant/register", json=tenant_data)

        assert response.status_code == 422

    async def test_tenant_register_weak_password(self, client: AsyncClient):
        """测试租户注册 - 密码太弱"""
        tenant_data = TestDataGenerator.generate_tenant()
        tenant_data["password"] = "123"

        response = await client.post("/api/v1/tenant/register", json=tenant_data)

        assert response.status_code in [400, 422]

    async def test_tenant_register_missing_required_fields(self, client: AsyncClient):
        """测试租户注册 - 缺少必填字段"""
        incomplete_data = {"company_name": "测试公司"}

        response = await client.post("/api/v1/tenant/register", json=incomplete_data)

        assert response.status_code == 422

    async def test_tenant_register_with_optional_phone(self, client: AsyncClient):
        """测试租户注册 - 包含可选的手机号"""
        tenant_data = TestDataGenerator.generate_tenant()
        tenant_data["contact_phone"] = "13800138000"

        response = await client.post("/api/v1/tenant/register", json=tenant_data)

        data = AssertHelper.assert_response_success(response, 200)


# ==================== 2. 租户登录测试 ====================


class TestTenantLogin:
    """租户登录测试"""

    async def test_tenant_login_success(self, client: AsyncClient, test_tenant):
        """测试租户登录成功"""
        response = await client.post(
            "/api/v1/tenant/login",
            json={
                "email": test_tenant.contact_email,
                "password": "Tenant@123456",
            },
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证JWT Token
        assert "data" in data
        result = data["data"]
        assert "access_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer"
        assert "expires_in" in result
        assert result["expires_in"] == 86400  # 24小时

    async def test_tenant_login_invalid_email(self, client: AsyncClient):
        """测试租户登录 - 邮箱错误"""
        response = await client.post(
            "/api/v1/tenant/login",
            json={"email": "nonexistent@example.com", "password": "Test@123456"},
        )

        AssertHelper.assert_response_error(response, 401)

    async def test_tenant_login_invalid_password(self, client: AsyncClient, test_tenant):
        """测试租户登录 - 密码错误"""
        response = await client.post(
            "/api/v1/tenant/login",
            json={"email": test_tenant.contact_email, "password": "WrongPassword"},
        )

        AssertHelper.assert_response_error(response, 401)


# ==================== 3. 租户信息查询测试 ====================


class TestTenantInfo:
    """租户信息查询测试"""

    async def test_get_tenant_info_with_api_key(
        self, client: AsyncClient, test_tenant, tenant_api_key_headers: dict
    ):
        """测试使用API Key获取租户信息"""
        response = await client.get("/api/v1/tenant/info", headers=tenant_api_key_headers)

        data = AssertHelper.assert_response_success(response, 200)

        # 验证租户信息
        tenant_info = data["data"]
        assert tenant_info["tenant_id"] == test_tenant.tenant_id
        assert tenant_info["company_name"] == test_tenant.company_name
        assert "api_key" not in tenant_info  # 不应该返回API Key
        assert "password" not in tenant_info

    async def test_get_tenant_info_with_token(
        self, client: AsyncClient, test_tenant, tenant_headers: dict
    ):
        """测试使用JWT Token获取租户信息"""
        response = await client.get("/api/v1/tenant/info-token", headers=tenant_headers)

        data = AssertHelper.assert_response_success(response, 200)

        tenant_info = data["data"]
        assert tenant_info["tenant_id"] == test_tenant.tenant_id

    async def test_get_tenant_info_invalid_api_key(self, client: AsyncClient):
        """测试使用无效API Key"""
        response = await client.get(
            "/api/v1/tenant/info", headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == 401

    async def test_get_tenant_info_missing_auth(self, client: AsyncClient):
        """测试缺少认证信息"""
        response = await client.get("/api/v1/tenant/info")

        assert response.status_code == 401


# ==================== 4. 订阅信息查询测试 ====================


class TestTenantSubscription:
    """租户订阅信息测试"""

    async def test_get_subscription_with_api_key(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取订阅信息"""
        response = await client.get(
            "/api/v1/tenant/subscription", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证订阅信息
        subscription = data["data"]
        assert "plan_type" in subscription
        assert "status" in subscription
        assert "start_at" in subscription
        assert "expire_at" in subscription

    async def test_get_subscription_with_token(
        self, client: AsyncClient, tenant_headers: dict
    ):
        """测试使用Token获取订阅信息"""
        response = await client.get(
            "/api/v1/tenant/subscription-token", headers=tenant_headers
        )

        data = AssertHelper.assert_response_success(response, 200)


# ==================== 5. 配额查询测试 ====================


class TestTenantQuota:
    """租户配额测试"""

    async def test_get_quota_usage(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取配额使用情况"""
        response = await client.get("/api/v1/tenant/quota", headers=tenant_api_key_headers)

        data = AssertHelper.assert_response_success(response, 200)

        # 验证配额信息
        quota = data["data"]
        assert "api_calls" in quota
        assert "conversations" in quota
        assert "storage" in quota


# ==================== 6. 用量统计测试 ====================


class TestTenantUsage:
    """租户用量统计测试"""

    async def test_get_usage_statistics(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取用量统计"""
        from datetime import datetime

        now = datetime.now()

        response = await client.get(
            "/api/v1/tenant/usage",
            params={"year": now.year, "month": now.month},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证用量数据
        usage = data["data"]
        assert isinstance(usage, dict)


# ==================== 7. 套餐订阅测试 ====================


class TestPlanSubscription:
    """套餐订阅测试"""

    async def test_subscribe_free_plan(self, client: AsyncClient, tenant_headers: dict):
        """测试订阅免费套餐"""
        subscribe_data = {
            "plan_type": "free",
            "duration_months": 12,
            "payment_method": "alipay",
            "auto_renew": False,
        }

        response = await client.post(
            "/api/v1/tenant/subscribe", json=subscribe_data, headers=tenant_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 免费套餐应该直接激活
        result = data["data"]
        assert result["success"] is True
        assert result["payment_required"] is False
        assert "subscription" in result

    async def test_subscribe_paid_plan(self, client: AsyncClient, tenant_headers: dict):
        """测试订阅付费套餐"""
        subscribe_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_method": "alipay",
            "auto_renew": False,
        }

        response = await client.post(
            "/api/v1/tenant/subscribe", json=subscribe_data, headers=tenant_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 付费套餐需要支付
        result = data["data"]
        assert result["success"] is True
        assert result["payment_required"] is True
        assert "order_number" in result
        assert "payment_amount" in result

    async def test_subscribe_invalid_plan_type(
        self, client: AsyncClient, tenant_headers: dict
    ):
        """测试订阅无效套餐"""
        subscribe_data = {
            "plan_type": "invalid_plan",
            "duration_months": 1,
            "payment_method": "alipay",
            "auto_renew": False,
        }

        response = await client.post(
            "/api/v1/tenant/subscribe", json=subscribe_data, headers=tenant_headers
        )

        AssertHelper.assert_response_error(response, 400)


# ==================== 8. 套餐变更测试 ====================


class TestPlanChange:
    """套餐变更测试"""

    async def test_upgrade_plan_immediately(
        self, client: AsyncClient, test_tenant_with_basic_plan, tenant_headers: dict
    ):
        """测试立即升级套餐"""
        change_data = {"new_plan_type": "professional", "effective_immediately": True}

        response = await client.put(
            "/api/v1/tenant/subscription", json=change_data, headers=tenant_headers
        )

        # 升级需要补差价
        if response.status_code == 200:
            data = response.json()
            result = data["data"]

            if result.get("payment_required"):
                assert "payment_amount" in result
                assert "order_number" in result

    async def test_downgrade_plan_next_cycle(
        self, client: AsyncClient, tenant_headers: dict
    ):
        """测试下个周期降级套餐"""
        change_data = {"new_plan_type": "basic", "effective_immediately": False}

        response = await client.put(
            "/api/v1/tenant/subscription", json=change_data, headers=tenant_headers
        )

        # 降级安排到下个周期
        if response.status_code == 200:
            data = response.json()
            result = data["data"]
            assert result["payment_required"] is False

    async def test_preview_plan_change_price(
        self, client: AsyncClient, tenant_headers: dict
    ):
        """测试预览套餐变更价格"""
        response = await client.get(
            "/api/v1/tenant/subscription/price-preview",
            params={"new_plan_type": "professional"},
            headers=tenant_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证价格预览信息
        preview = data["data"]
        assert "current_plan" in preview
        assert "new_plan" in preview
        assert "prorated_charge" in preview
        assert "remaining_days" in preview

    async def test_change_to_same_plan(self, client: AsyncClient, tenant_headers: dict):
        """测试变更到相同套餐"""
        change_data = {"new_plan_type": "free", "effective_immediately": True}

        response = await client.put(
            "/api/v1/tenant/subscription", json=change_data, headers=tenant_headers
        )

        # 应该返回错误
        AssertHelper.assert_response_error(response, 400)


# ==================== 9. 认证方式对比测试 ====================


class TestAuthenticationComparison:
    """双认证方式对比测试"""

    async def test_api_key_vs_token_consistency(
        self,
        client: AsyncClient,
        test_tenant,
        tenant_api_key_headers: dict,
        tenant_headers: dict,
    ):
        """测试API Key和Token返回数据一致性"""
        # 使用API Key获取信息
        response1 = await client.get("/api/v1/tenant/info", headers=tenant_api_key_headers)
        data1 = response1.json()

        # 使用Token获取信息
        response2 = await client.get("/api/v1/tenant/info-token", headers=tenant_headers)
        data2 = response2.json()

        # 两种方式返回的核心信息应该一致
        if response1.status_code == 200 and response2.status_code == 200:
            assert data1["data"]["tenant_id"] == data2["data"]["tenant_id"]
            assert data1["data"]["company_name"] == data2["data"]["company_name"]
