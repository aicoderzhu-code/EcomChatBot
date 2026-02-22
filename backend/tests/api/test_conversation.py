"""
对话管理测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, ConversationTestMixin
from utils.assertions import assert_paginated


@pytest.mark.conversation
class TestConversation(BaseAPITest, TenantTestMixin, ConversationTestMixin):
    """对话管理测试"""

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        """测试创建对话"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建对话
        user_data = self.data_gen.generate_user()
        response = await self.client.post(
            "/conversation/create",
            json=user_data
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "conversation_id" in data
        # API 返回的是内部 user_id (int)，不是 user_external_id
        assert "user_id" in data
        assert data["channel"] == user_data["channel"]
        assert data["status"] == "active"

        # 注册清理
        self.cleaner.register_conversation(data["conversation_id"])

    @pytest.mark.asyncio
    async def test_list_conversations(self):
        """测试查询对话列表"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建几个对话
        for i in range(3):
            await self.create_test_conversation()

        # 查询对话列表
        response = await self.client.get(
            "/conversation/list",
            params={"page": 1, "size": 10}
        )

        data = self.assert_success(response)

        # 验证分页数据
        assert_paginated(data, min_total=3)
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self):
        """测试获取对话详情"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 获取对话详情
        response = await self.client.get(f"/conversation/{conversation_id}")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["conversation_id"] == conversation_id
        assert "messages" in data
        assert "user" in data

    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 发送消息
        message_data = {"content": "你好，这是一条测试消息"}
        response = await self.client.post(
            f"/conversation/{conversation_id}/messages",
            json=message_data
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "message_id" in data
        assert "content" in data
        assert data["role"] in ["user", "assistant"]

    @pytest.mark.asyncio
    async def test_get_messages(self):
        """测试获取消息列表"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 发送消息
        await self.client.post(
            f"/conversation/{conversation_id}/messages",
            json={"content": "测试消息1"}
        )

        # 获取消息列表
        response = await self.client.get(
            f"/conversation/{conversation_id}/messages",
            params={"limit": 50}
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_close_conversation(self):
        """测试关闭对话"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 关闭对话
        update_data = {
            "status": "closed",
            "satisfaction_score": 5,
            "feedback": "服务很好"
        }
        response = await self.client.put(
            f"/conversation/{conversation_id}",
            json=update_data
        )

        data = self.assert_success(response)

        # 验证状态已更新
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_conversation_with_satisfaction(self):
        """测试对话评价"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 关闭对话并评价
        update_data = {
            "status": "closed",
            "satisfaction_score": 4,
            "feedback": "还不错"
        }
        response = await self.client.put(
            f"/conversation/{conversation_id}",
            json=update_data
        )

        data = self.assert_success(response)
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_list_conversations_by_user(self):
        """测试按用户查询对话列表"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建特定用户的对话
        user_id = f"test_user_{int(__import__('time').time())}"
        await self.create_test_conversation(user_id)

        # 按用户ID查询
        response = await self.client.get(
            "/conversation/list",
            params={"user_id": user_id, "page": 1, "size": 10}
        )

        data = self.assert_success(response)
        assert_paginated(data, min_total=1)

    @pytest.mark.asyncio
    async def test_list_conversations_by_status(self):
        """测试按状态查询对话列表"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建并关闭一个对话
        conversation_id = await self.create_test_conversation()
        await self.client.put(
            f"/conversation/{conversation_id}",
            json={"status": "closed"}
        )

        # 按状态查询
        response = await self.client.get(
            "/conversation/list",
            params={"status": "closed", "page": 1, "size": 10}
        )

        data = self.assert_success(response)
        assert isinstance(data["items"], list)
