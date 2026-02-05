"""
租户认证测试
"""
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from services import TenantService


class TestTenantRegister:
    """租户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试正常注册"""
        response = await client.post(
            "/api/v1/auth/register",
            json=test_tenant_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tenant_id" in data["data"]
        assert "api_key" in data["data"]
        assert data["data"]["message"] == "注册成功"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试重复邮箱注册"""
        # 第一次注册
        await client.post("/api/v1/auth/register", json=test_tenant_data)

        # 第二次注册相同邮箱
        response = await client.post("/api/v1/auth/register", json=test_tenant_data)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "DUPLICATE" in data["error"]["code"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试无效邮箱格式"""
        test_tenant_data["contact_email"] = "invalid-email"

        response = await client.post("/api/v1/auth/register", json=test_tenant_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试密码过短"""
        test_tenant_data["password"] = "short"

        response = await client.post("/api/v1/auth/register", json=test_tenant_data)

        assert response.status_code == 422


class TestTenantLogin:
    """租户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试正常登录"""
        # 先注册
        await client.post("/api/v1/auth/register", json=test_tenant_data)

        # 登录
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": test_tenant_data["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试密码错误"""
        # 先注册
        await client.post("/api/v1/auth/register", json=test_tenant_data)

        # 使用错误密码登录
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(
        self,
        client: AsyncClient,
    ):
        """测试不存在的邮箱"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


class TestTokenRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试正常刷新 Token"""
        # 注册并登录
        await client.post("/api/v1/auth/register", json=test_tenant_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": test_tenant_data["password"],
            },
        )
        login_data = login_response.json()["data"]

        # 刷新 Token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(
        self,
        client: AsyncClient,
    ):
        """测试无效的刷新 Token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 400


class TestTenantLogout:
    """租户登出测试"""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试正常登出"""
        # 注册并登录
        await client.post("/api/v1/auth/register", json=test_tenant_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": test_tenant_data["password"],
            },
        )
        login_data = login_response.json()["data"]

        # 登出
        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login_data["refresh_token"]},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["message"] == "登出成功"

    @pytest.mark.asyncio
    async def test_refresh_after_logout(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试登出后刷新 Token"""
        # 注册并登录
        await client.post("/api/v1/auth/register", json=test_tenant_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": test_tenant_data["password"],
            },
        )
        login_data = login_response.json()["data"]

        # 登出
        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": login_data["refresh_token"]},
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )

        # 尝试使用旧的 refresh_token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )

        assert response.status_code == 400


class TestAccountLocking:
    """账户锁定测试"""

    @pytest.mark.asyncio
    async def test_account_lock_after_failed_attempts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant_data: dict[str, Any],
    ):
        """测试多次失败后锁定账户"""
        # 注册
        await client.post("/api/v1/auth/register", json=test_tenant_data)

        # 连续5次错误登录
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_tenant_data["contact_email"],
                    "password": "wrongpassword",
                },
            )

        # 第6次应该被锁定
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_tenant_data["contact_email"],
                "password": test_tenant_data["password"],  # 即使密码正确也应该被锁定
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "锁定" in data["error"]["message"] or "locked" in data["error"]["message"].lower()
