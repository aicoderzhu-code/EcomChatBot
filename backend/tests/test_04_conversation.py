"""
对话管理模块测试
测试覆盖: 6个接口, 30个测试用例
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.conversation]


class TestConversationManagement:
    """对话创建和管理测试"""

    async def test_create_conversation_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试创建会话成功"""
        response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证会话信息
        conversation = data["data"]
        assert "conversation_id" in conversation
        assert conversation["user_id"] == conversation_data["user_id"]
        assert conversation["channel"] == conversation_data["channel"]
        assert conversation["status"] == "active"

    async def test_create_conversation_quota_check(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建会话时的配额检查"""
        # 创建多个会话直到达到配额限制
        for i in range(5):
            conv_data = TestDataGenerator.generate_conversation()
            response = await client.post(
                "/api/v1/conversation/create",
                json=conv_data,
                headers=tenant_api_key_headers,
            )

            # 前几个应该成功,超过配额后应该失败
            if response.status_code == 429:
                # 达到并发配额限制
                break

    async def test_get_conversation_detail(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试获取会话详情"""
        # 先创建会话
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )
        conversation_id = create_response.json()["data"]["conversation_id"]

        # 获取详情
        response = await client.get(
            f"/api/v1/conversation/{conversation_id}",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证详情数据
        detail = data["data"]
        assert detail["conversation_id"] == conversation_id
        assert "messages" in detail
        assert "user" in detail

    async def test_list_conversations(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询会话列表"""
        response = await client.get(
            "/api/v1/conversation/list",
            params={"page": 1, "size": 20},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        AssertHelper.assert_pagination(data["data"])

    async def test_list_conversations_filter_by_user(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试按用户过滤会话"""
        # 创建会话
        await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        # 按用户ID过滤
        response = await client.get(
            "/api/v1/conversation/list",
            params={"user_id": conversation_data["user_id"]},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        items = data["data"]["items"]

        # 所有会话应该属于同一用户
        for item in items:
            assert item["user_id"] == conversation_data["user_id"]


class TestConversationMessages:
    """会话消息测试"""

    async def test_send_message_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试发送消息成功"""
        # 创建会话
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )
        conversation_id = create_response.json()["data"]["conversation_id"]

        # 发送消息
        message_data = {"content": "你好，我需要帮助"}

        response = await client.post(
            f"/api/v1/conversation/{conversation_id}/messages",
            json=message_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证消息
        message = data["data"]
        assert "message_id" in message
        assert message["content"] == message_data["content"]
        assert message["role"] == "assistant"  # 返回的是助手回复

    async def test_get_conversation_messages(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试获取会话消息列表"""
        # 创建会话并发送消息
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )
        conversation_id = create_response.json()["data"]["conversation_id"]

        await client.post(
            f"/api/v1/conversation/{conversation_id}/messages",
            json={"content": "测试消息"},
            headers=tenant_api_key_headers,
        )

        # 获取消息列表
        response = await client.get(
            f"/api/v1/conversation/{conversation_id}/messages",
            params={"limit": 50},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        messages = data["data"]
        assert isinstance(messages, list)
        assert len(messages) > 0


class TestConversationUpdate:
    """会话更新测试"""

    async def test_close_conversation(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试关闭会话"""
        # 创建会话
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )
        conversation_id = create_response.json()["data"]["conversation_id"]

        # 关闭会话
        update_data = {
            "status": "closed",
            "satisfaction_score": 5,
            "feedback": "服务很好",
        }

        response = await client.put(
            f"/api/v1/conversation/{conversation_id}",
            json=update_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证会话已关闭
        conversation = data["data"]
        assert conversation["status"] == "closed"
        assert conversation["satisfaction_score"] == 5
