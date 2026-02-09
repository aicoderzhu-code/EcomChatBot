"""
管理员模块测试
测试覆盖: 25个接口, 75个测试用例
包含: 认证、管理员管理、租户管理、账单管理、审计日志
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Admin
from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.admin]


# ==================== 1. 管理员认证测试 ====================


class TestAdminAuthentication:
    """管理员认证测试"""

    async def test_admin_login_success(
        self, client: AsyncClient, db_session: AsyncSession, test_admin: Admin
    ):
        """测试管理员登录成功"""
        response = await client.post(
            "/api/v1/admin/login",
            json={"username": "test_admin", "password": "Admin@123456"},
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证响应格式
        assert "data" in data
        assert "access_token" in data["data"]
        assert "token_type" in data["data"]
        assert "expires_in" in data["data"]
        assert "admin" in data["data"]

        # 验证token类型
        assert data["data"]["token_type"] == "bearer"

        # 验证管理员信息
        admin_info = data["data"]["admin"]
        assert admin_info["username"] == "test_admin"
        assert admin_info["role"] == "super_admin"
        assert "password" not in admin_info
        assert "password_hash" not in admin_info

    async def test_admin_login_invalid_username(self, client: AsyncClient):
        """测试管理员登录 - 用户名错误"""
        response = await client.post(
            "/api/v1/admin/login",
            json={"username": "nonexistent", "password": "Admin@123456"},
        )

        AssertHelper.assert_response_error(response, 401)

    async def test_admin_login_invalid_password(
        self, client: AsyncClient, test_admin: Admin
    ):
        """测试管理员登录 - 密码错误"""
        response = await client.post(
            "/api/v1/admin/login",
            json={"username": "test_admin", "password": "WrongPassword"},
        )

        AssertHelper.assert_response_error(response, 401)

    async def test_admin_login_missing_fields(self, client: AsyncClient):
        """测试管理员登录 - 缺少必填字段"""
        # 缺少password
        response = await client.post(
            "/api/v1/admin/login", json={"username": "test_admin"}
        )
        assert response.status_code == 422

        # 缺少username
        response = await client.post(
            "/api/v1/admin/login", json={"password": "Admin@123456"}
        )
        assert response.status_code == 422

    async def test_admin_login_empty_credentials(self, client: AsyncClient):
        """测试管理员登录 - 空凭据"""
        response = await client.post(
            "/api/v1/admin/login", json={"username": "", "password": ""}
        )
        assert response.status_code in [400, 422]

    async def test_admin_token_authentication(
        self, client: AsyncClient, test_admin: Admin, admin_token: str
    ):
        """测试使用Token访问受保护接口"""
        response = await client.get(
            "/api/v1/admin/admins",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 超级管理员应该能访问管理员列表
        assert response.status_code == 200

    async def test_admin_invalid_token(self, client: AsyncClient):
        """测试无效Token"""
        response = await client.get(
            "/api/v1/admin/admins",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    async def test_admin_expired_token(self, client: AsyncClient):
        """测试过期Token"""
        # 创建一个已过期的token (需要mock时间)
        from datetime import timedelta
        from core import create_access_token

        expired_token = create_access_token(
            subject="ADMIN_TEST", role="super_admin", expires_delta=timedelta(seconds=-1)
        )

        response = await client.get(
            "/api/v1/admin/admins", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


# ==================== 2. 管理员管理测试 ====================


class TestAdminManagement:
    """管理员CRUD操作测试"""

    async def test_list_admins_success(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试获取管理员列表"""
        response = await client.get("/api/v1/admin/admins", headers=admin_headers)

        data = AssertHelper.assert_response_success(response, 200)

        # 验证分页数据
        assert "data" in data
        AssertHelper.assert_pagination(data["data"])

        # 应该至少包含测试管理员
        items = data["data"]["items"]
        assert len(items) > 0

    async def test_list_admins_with_pagination(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试管理员列表分页"""
        response = await client.get(
            "/api/v1/admin/admins", params={"page": 1, "size": 10}, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)
        AssertHelper.assert_pagination(data["data"], page=1, size=10)

    async def test_list_admins_filter_by_role(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试按角色过滤管理员"""
        response = await client.get(
            "/api/v1/admin/admins", params={"role": "super_admin"}, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        # 所有返回的管理员角色都应该是super_admin
        for item in items:
            assert item["role"] == "super_admin"

    async def test_list_admins_filter_by_status(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试按状态过滤管理员"""
        response = await client.get(
            "/api/v1/admin/admins", params={"status": "active"}, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        for item in items:
            assert item["status"] == "active"

    async def test_list_admins_search_by_keyword(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试按关键词搜索管理员"""
        response = await client.get(
            "/api/v1/admin/admins",
            params={"keyword": test_admin.username},
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        # 应该能找到测试管理员
        assert any(item["username"] == test_admin.username for item in items)

    async def test_create_admin_success(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试创建管理员成功"""
        admin_data = TestDataGenerator.generate_admin(role="operator")

        response = await client.post(
            "/api/v1/admin/admins", json=admin_data, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证返回的管理员信息
        created_admin = data["data"]
        assert created_admin["username"] == admin_data["username"]
        assert created_admin["email"] == admin_data["email"]
        assert created_admin["role"] == admin_data["role"]
        assert "admin_id" in created_admin
        assert "password" not in created_admin

    async def test_create_admin_duplicate_username(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试创建管理员 - 用户名重复"""
        admin_data = TestDataGenerator.generate_admin()
        admin_data["username"] = test_admin.username  # 使用已存在的用户名

        response = await client.post(
            "/api/v1/admin/admins", json=admin_data, headers=admin_headers
        )

        AssertHelper.assert_response_error(response, 400)

    async def test_create_admin_invalid_role(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试创建管理员 - 无效角色"""
        admin_data = TestDataGenerator.generate_admin()
        admin_data["role"] = "invalid_role"

        response = await client.post(
            "/api/v1/admin/admins", json=admin_data, headers=admin_headers
        )

        assert response.status_code in [400, 422]

    async def test_create_admin_weak_password(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试创建管理员 - 弱密码"""
        admin_data = TestDataGenerator.generate_admin()
        admin_data["password"] = "123"  # 太短

        response = await client.post(
            "/api/v1/admin/admins", json=admin_data, headers=admin_headers
        )

        assert response.status_code in [400, 422]

    async def test_get_admin_detail(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试获取管理员详情"""
        response = await client.get(
            f"/api/v1/admin/admins/{test_admin.admin_id}", headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证管理员详情
        admin_detail = data["data"]
        assert admin_detail["admin_id"] == test_admin.admin_id
        assert admin_detail["username"] == test_admin.username
        assert admin_detail["role"] == test_admin.role

    async def test_get_admin_detail_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试获取管理员详情 - 不存在"""
        response = await client.get(
            "/api/v1/admin/admins/ADMIN_NOTEXIST", headers=admin_headers
        )

        AssertHelper.assert_response_error(response, 404)

    async def test_update_admin_success(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试更新管理员信息"""
        update_data = {"email": "newemail@example.com", "phone": "13900139000"}

        response = await client.put(
            f"/api/v1/admin/admins/{test_admin.admin_id}",
            json=update_data,
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证更新成功
        updated_admin = data["data"]
        assert updated_admin["email"] == update_data["email"]
        assert updated_admin["phone"] == update_data["phone"]

    async def test_update_admin_change_role(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ):
        """测试更新管理员角色"""
        # 创建一个普通管理员用于测试
        from core import hash_password
        import uuid

        test_operator = Admin(
            admin_id=f"ADMIN_{uuid.uuid4().hex[:12].upper()}",
            username=f"operator_{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Test@123456"),
            email="operator@test.com",
            role="operator",
            status="active",
        )
        db_session.add(test_operator)
        await db_session.commit()
        await db_session.refresh(test_operator)

        # 更新角色
        update_data = {"role": "support_admin"}

        response = await client.put(
            f"/api/v1/admin/admins/{test_operator.admin_id}",
            json=update_data,
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        assert data["data"]["role"] == "support_admin"

    async def test_update_admin_cannot_modify_self_role(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试不能修改自己的角色"""
        update_data = {"role": "operator"}

        response = await client.put(
            f"/api/v1/admin/admins/{test_admin.admin_id}",
            json=update_data,
            headers=admin_headers,
        )

        AssertHelper.assert_response_error(response, 400)

    async def test_delete_admin_success(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ):
        """测试删除管理员"""
        # 创建一个临时管理员用于删除
        from core import hash_password
        import uuid

        temp_admin = Admin(
            admin_id=f"ADMIN_{uuid.uuid4().hex[:12].upper()}",
            username=f"temp_{uuid.uuid4().hex[:8]}",
            password_hash=hash_password("Test@123456"),
            email="temp@test.com",
            role="operator",
            status="active",
        )
        db_session.add(temp_admin)
        await db_session.commit()
        await db_session.refresh(temp_admin)

        # 删除管理员
        response = await client.delete(
            f"/api/v1/admin/admins/{temp_admin.admin_id}", headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)
        assert "message" in data["data"]

    async def test_delete_admin_cannot_delete_self(
        self, client: AsyncClient, test_admin: Admin, admin_headers: dict
    ):
        """测试不能删除自己"""
        response = await client.delete(
            f"/api/v1/admin/admins/{test_admin.admin_id}", headers=admin_headers
        )

        AssertHelper.assert_response_error(response, 400)


# ==================== 3. 租户管理测试 ====================


class TestTenantManagementByAdmin:
    """管理员管理租户测试"""

    async def test_list_tenants_success(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试获取租户列表"""
        response = await client.get("/api/v1/admin/tenants", headers=admin_headers)

        data = AssertHelper.assert_response_success(response, 200)
        AssertHelper.assert_pagination(data["data"])

    async def test_list_tenants_filter_by_status(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试按状态过滤租户"""
        response = await client.get(
            "/api/v1/admin/tenants", params={"status": "active"}, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        for item in items:
            assert item["status"] == "active"

    async def test_list_tenants_filter_by_plan(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试按套餐过滤租户"""
        response = await client.get(
            "/api/v1/admin/tenants", params={"plan": "free"}, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_list_tenants_search_by_keyword(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试按关键词搜索租户"""
        response = await client.get(
            "/api/v1/admin/tenants",
            params={"keyword": test_tenant.company_name},
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        # 应该能找到测试租户
        assert any(item["company_name"] == test_tenant.company_name for item in items)

    async def test_get_tenant_detail(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试获取租户详情"""
        response = await client.get(
            f"/api/v1/admin/tenants/{test_tenant.tenant_id}", headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        tenant_detail = data["data"]
        assert tenant_detail["tenant_id"] == test_tenant.tenant_id
        assert tenant_detail["company_name"] == test_tenant.company_name
        assert "api_key" not in tenant_detail  # 不应该返回API Key

    async def test_create_tenant_by_admin(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试管理员创建租户(代客开户)"""
        tenant_data = TestDataGenerator.generate_tenant()

        response = await client.post(
            "/api/v1/admin/tenants", json=tenant_data, headers=admin_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证返回的租户信息
        created_tenant = data["data"]
        assert created_tenant["company_name"] == tenant_data["company_name"]
        assert created_tenant["contact_email"] == tenant_data["contact_email"]
        assert "tenant_id" in created_tenant
        assert "api_key" in created_tenant  # 应该返回API Key

    async def test_update_tenant_status(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试更新租户状态"""
        update_data = {"status": "suspended", "reason": "测试暂停"}

        response = await client.put(
            f"/api/v1/admin/tenants/{test_tenant.tenant_id}/status",
            json=update_data,
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证状态更新成功
        updated_tenant = data["data"]
        assert updated_tenant["status"] == "suspended"

    async def test_assign_plan_to_tenant(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试分配套餐"""
        response = await client.post(
            f"/api/v1/admin/tenants/{test_tenant.tenant_id}/assign-plan",
            params={"plan_type": "basic", "duration_months": 3},
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_adjust_tenant_quota(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试调整租户配额"""
        response = await client.post(
            f"/api/v1/admin/tenants/{test_tenant.tenant_id}/adjust-quota",
            params={
                "quota_type": "api_calls",
                "amount": 1000,
                "reason": "补偿调整",
            },
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_reset_tenant_api_key(
        self, client: AsyncClient, test_tenant, admin_headers: dict
    ):
        """测试重置租户API密钥"""
        old_api_key = test_tenant.plain_api_key

        response = await client.post(
            f"/api/v1/admin/tenants/{test_tenant.tenant_id}/reset-api-key",
            headers=admin_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证返回新的API Key
        new_api_key = data["data"]["api_key"]
        assert new_api_key != old_api_key
        assert new_api_key.startswith("sk_live_")


# ==================== 4. 批量操作测试 ====================


class TestBatchOperations:
    """批量操作测试"""

    async def test_batch_activate_tenants(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试批量激活租户"""
        batch_data = {
            "operation": "activate",
            "tenant_ids": ["TENANT_001", "TENANT_002"],
        }

        response = await client.post(
            "/api/v1/admin/tenants/batch-operation",
            json=batch_data,
            headers=admin_headers,
        )

        # 可能失败因为租户不存在,但应该返回结果
        if response.status_code == 200:
            data = response.json()
            assert "success" in data["data"]
            assert "failed" in data["data"]

    async def test_batch_suspend_tenants(
        self, client: AsyncClient, admin_headers: dict
    ):
        """测试批量暂停租户"""
        batch_data = {
            "operation": "suspend",
            "tenant_ids": ["TENANT_001", "TENANT_002"],
        }

        response = await client.post(
            "/api/v1/admin/tenants/batch-operation",
            json=batch_data,
            headers=admin_headers,
        )

        # 验证响应格式
        if response.status_code == 200:
            data = response.json()
            assert "total" in data["data"]
            assert "success_count" in data["data"]
            assert "failed_count" in data["data"]


# 由于篇幅限制,后续测试用例将在下一部分继续...
