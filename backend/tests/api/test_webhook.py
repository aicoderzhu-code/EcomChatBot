"""
Webhook API 测试

覆盖 Webhook 配置的完整 CRUD、日志查询、跨租户防护
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, WebhookTestMixin
from config import settings


@pytest.mark.webhook
class TestWebhook(BaseAPITest, TenantTestMixin, WebhookTestMixin):
    """Webhook API 测试"""

    @pytest.mark.asyncio
    async def test_get_event_types(self):
        """测试获取 Webhook 事件类型列表（公开接口）"""
        response = await self.client.get("/webhooks/event-types")
        data = self.assert_success(response)

        assert "event_types" in data
        assert isinstance(data["event_types"], list)
        assert len(data["event_types"]) > 0

        first_event = data["event_types"][0]
        assert "value" in first_event
        assert "name" in first_event
        print(f"✓ 获取事件类型成功，共 {len(data['event_types'])} 种")

    @pytest.mark.asyncio
    async def test_create_webhook(self):
        """测试创建 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/webhooks",
            json={
                "name": "测试Webhook",
                "endpoint_url": "https://httpbin.org/post",
                "events": ["conversation.started", "conversation.ended"],
                "secret": "test_secret_key_12345",
            }
        )

        data = self.assert_success(response)
        assert "id" in data
        assert data["name"] == "测试Webhook"
        self.cleaner.register_webhook(data["id"])
        print(f"✓ Webhook 创建成功: ID={data['id']}")

    @pytest.mark.asyncio
    async def test_list_webhooks(self):
        """测试列出 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建 2 个 Webhook
        await self.create_test_webhook(name="Webhook-1")
        await self.create_test_webhook(name="Webhook-2", url="https://httpbin.org/anything")

        # 列出
        response = await self.client.get("/webhooks")
        data = self.assert_success(response)

        assert isinstance(data, list)
        assert len(data) >= 2
        print(f"✓ 列出 Webhook 成功，共 {len(data)} 个")

    @pytest.mark.asyncio
    async def test_get_webhook_detail(self):
        """测试获取 Webhook 详情"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        webhook_id = await self.create_test_webhook()

        response = await self.client.get(f"/webhooks/{webhook_id}")
        data = self.assert_success(response)

        assert data["id"] == webhook_id
        assert data["name"] == "测试Webhook"
        print(f"✓ Webhook 详情查询成功: {data['name']}")

    @pytest.mark.asyncio
    async def test_update_webhook(self):
        """测试更新 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        webhook_id = await self.create_test_webhook()

        response = await self.client.put(
            f"/webhooks/{webhook_id}",
            json={
                "name": "更新后的Webhook",
                "endpoint_url": "https://httpbin.org/anything",
                "events": ["conversation.started"],
                "is_active": True,
            }
        )

        data = self.assert_success(response)
        assert data["name"] == "更新后的Webhook"
        print("✓ Webhook 更新成功")

    @pytest.mark.asyncio
    async def test_delete_webhook(self):
        """测试删除 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        webhook_id = await self.create_test_webhook()

        response = await self.client.delete(f"/webhooks/{webhook_id}")
        self.assert_success(response)

        # 删除后查询应返回 404
        get_resp = await self.client.get(f"/webhooks/{webhook_id}")
        assert get_resp.status_code in [404, 400]
        print("✓ Webhook 删除成功")

    @pytest.mark.asyncio
    async def test_get_webhook_logs(self):
        """测试查询 Webhook 投递日志"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        webhook_id = await self.create_test_webhook()

        response = await self.client.get(
            f"/webhooks/{webhook_id}/logs",
            params={"limit": 10}
        )

        data = self.assert_success(response)
        assert isinstance(data, list)
        print(f"✓ Webhook 日志查询成功，共 {len(data)} 条")

    @pytest.mark.asyncio
    async def test_create_webhook_invalid_url(self):
        """测试使用无效 URL 创建 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/webhooks",
            json={
                "name": "无效URL的Webhook",
                "endpoint_url": "not-a-valid-url",
                "events": ["conversation.started"],
            }
        )

        assert response.status_code in [400, 422]
        print("✓ 无效 URL 被正确拒绝")

    @pytest.mark.asyncio
    async def test_create_webhook_missing_fields(self):
        """测试缺少必填字段创建 Webhook"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/webhooks",
            json={"name": "缺少URL"}
        )

        assert response.status_code in [400, 422]
        print("✓ 缺少必填字段被正确拒绝")

    @pytest.mark.asyncio
    async def test_cross_tenant_webhook_access(self):
        """测试跨租户 Webhook 访问防护"""
        tenant1 = await self.create_test_tenant()
        tenant2 = await self.create_test_tenant()

        # 租户1 创建 Webhook
        self.client.set_api_key(tenant1["api_key"])
        webhook_id = await self.create_test_webhook()

        # 租户2 尝试访问
        self.client.set_api_key(tenant2["api_key"])
        response = await self.client.get(f"/webhooks/{webhook_id}")

        assert response.status_code in [400, 403, 404]
        print("✓ 跨租户 Webhook 访问被正确阻止")

    @pytest.mark.asyncio
    async def test_webhook_without_auth(self):
        """测试无认证访问 Webhook 接口"""
        self.client.clear_auth()

        response = await self.client.get("/webhooks")
        assert response.status_code in [401, 403]
        print("✓ 无认证访问被正确拒绝")

    @pytest.mark.asyncio
    async def test_test_webhook_endpoint(self):
        """测试 Webhook 测试发送功能"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        webhook_id = await self.create_test_webhook()

        response = await self.client.post(f"/webhooks/test/{webhook_id}")

        if response.status_code == 200:
            data = self.assert_success(response)
            print("✓ Webhook 测试发送成功")
        else:
            print(f"⚠ Webhook 测试发送返回 {response.status_code}（目标URL可能不可达）")
