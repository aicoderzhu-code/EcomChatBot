"""
Webhook 功能测试
"""
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from services import TenantService


class TestWebhookCRUD:
    """Webhook CRUD 操作测试"""

    async def _create_tenant_and_get_api_key(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ) -> str:
        """创建租户并获取 API Key"""
        response = await client.post("/api/v1/auth/register", json=test_tenant_data)
        return response.json()["data"]["api_key"]

    @pytest.mark.asyncio
    async def test_get_event_types(
        self,
        client: AsyncClient,
    ):
        """测试获取事件类型"""
        response = await client.get("/api/v1/webhooks/event-types")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_types" in data["data"]
        assert len(data["data"]["event_types"]) > 0

        # 检查事件类型结构
        event_type = data["data"]["event_types"][0]
        assert "value" in event_type
        assert "name" in event_type
        assert "description" in event_type

    @pytest.mark.asyncio
    async def test_create_webhook(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试创建 Webhook"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == test_webhook_data["name"]
        assert data["data"]["url"] == test_webhook_data["url"]
        assert data["data"]["event_type"] == test_webhook_data["event_type"]
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_webhook_without_auth(
        self,
        client: AsyncClient,
        test_webhook_data: dict[str, Any],
    ):
        """测试未认证创建 Webhook"""
        response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_webhooks(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试列表查询 Webhook"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建多个 Webhook
        for i in range(3):
            webhook_data = test_webhook_data.copy()
            webhook_data["name"] = f"Webhook {i}"
            await client.post(
                "/api/v1/webhooks",
                json=webhook_data,
                headers={"X-API-Key": api_key},
            )

        # 查询列表
        response = await client.get(
            "/api/v1/webhooks",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 3
        assert len(data["data"]["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_webhook(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试获取 Webhook 详情"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 获取详情
        response = await client.get(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == webhook_id

    @pytest.mark.asyncio
    async def test_update_webhook(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试更新 Webhook"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 更新 Webhook
        update_data = {
            "name": "更新后的名称",
            "timeout": 60,
        }
        response = await client.put(
            f"/api/v1/webhooks/{webhook_id}",
            json=update_data,
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "更新后的名称"
        assert data["data"]["timeout"] == 60

    @pytest.mark.asyncio
    async def test_delete_webhook(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试删除 Webhook"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 删除 Webhook
        response = await client.delete(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200

        # 确认已删除
        get_response = await client.get(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"X-API-Key": api_key},
        )
        assert get_response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_not_found(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ):
        """测试访问不存在的 Webhook"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        response = await client.get(
            "/api/v1/webhooks/99999",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 400


class TestWebhookTest:
    """Webhook 测试功能测试"""

    async def _create_tenant_and_get_api_key(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ) -> str:
        """创建租户并获取 API Key"""
        response = await client.post("/api/v1/auth/register", json=test_tenant_data)
        return response.json()["data"]["api_key"]

    @pytest.mark.asyncio
    async def test_test_webhook_success(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试 Webhook 测试推送（模拟成功）"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook（使用测试 URL）
        test_webhook_data["url"] = "https://httpbin.org/post"
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 测试 Webhook
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"success": true}'
            mock_response.headers = {"Content-Type": "application/json"}
            mock_post.return_value = mock_response

            response = await client.post(
                f"/api/v1/webhooks/{webhook_id}/test",
                headers={"X-API-Key": api_key},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_test_webhook_with_custom_payload(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试使用自定义负载"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 使用自定义负载测试
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"received": true}'
            mock_response.headers = {}
            mock_post.return_value = mock_response

            response = await client.post(
                f"/api/v1/webhooks/{webhook_id}/test",
                json={"payload": {"custom": "data"}},
                headers={"X-API-Key": api_key},
            )

        assert response.status_code == 200


class TestWebhookLogs:
    """Webhook 日志测试"""

    async def _create_tenant_and_get_api_key(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ) -> str:
        """创建租户并获取 API Key"""
        response = await client.post("/api/v1/auth/register", json=test_tenant_data)
        return response.json()["data"]["api_key"]

    @pytest.mark.asyncio
    async def test_get_webhook_logs(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试获取 Webhook 日志"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 获取日志（可能为空）
        response = await client.get(
            f"/api/v1/webhooks/{webhook_id}/logs",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]


class TestWebhookFiltering:
    """Webhook 筛选测试"""

    async def _create_tenant_and_get_api_key(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
    ) -> str:
        """创建租户并获取 API Key"""
        response = await client.post("/api/v1/auth/register", json=test_tenant_data)
        return response.json()["data"]["api_key"]

    @pytest.mark.asyncio
    async def test_filter_by_event_type(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试按事件类型筛选"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建不同事件类型的 Webhook
        webhook1 = test_webhook_data.copy()
        webhook1["event_type"] = "conversation.created"
        await client.post(
            "/api/v1/webhooks",
            json=webhook1,
            headers={"X-API-Key": api_key},
        )

        webhook2 = test_webhook_data.copy()
        webhook2["event_type"] = "message.received"
        await client.post(
            "/api/v1/webhooks",
            json=webhook2,
            headers={"X-API-Key": api_key},
        )

        # 筛选特定事件类型
        response = await client.get(
            "/api/v1/webhooks",
            params={"event_type": "conversation.created"},
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["event_type"] == "conversation.created"

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self,
        client: AsyncClient,
        test_tenant_data: dict[str, Any],
        test_webhook_data: dict[str, Any],
    ):
        """测试按状态筛选"""
        api_key = await self._create_tenant_and_get_api_key(client, test_tenant_data)

        # 创建 Webhook
        create_response = await client.post(
            "/api/v1/webhooks",
            json=test_webhook_data,
            headers={"X-API-Key": api_key},
        )
        webhook_id = create_response.json()["data"]["id"]

        # 禁用 Webhook
        await client.put(
            f"/api/v1/webhooks/{webhook_id}",
            json={"status": "inactive"},
            headers={"X-API-Key": api_key},
        )

        # 筛选活跃状态
        response = await client.get(
            "/api/v1/webhooks",
            params={"status": "active"},
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0

        # 筛选非活跃状态
        response = await client.get(
            "/api/v1/webhooks",
            params={"status": "inactive"},
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
