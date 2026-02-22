"""
AI 对话测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, ConversationTestMixin, ModelConfigTestMixin
from config import settings


@pytest.mark.ai_chat
class TestAIChat(BaseAPITest, TenantTestMixin, ConversationTestMixin, ModelConfigTestMixin):
    """AI 对话测试"""

    def _get_llm_api_key(self):
        """获取当前 LLM 提供商的 API Key"""
        if settings.llm_provider == "zhipuai":
            return settings.zhipuai_api_key
        elif settings.llm_provider == "deepseek":
            return settings.deepseek_api_key
        elif settings.llm_provider == "openai":
            return settings.openai_api_key
        return settings.openai_api_key

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_ai_chat_basic(self):
        """测试基础AI对话"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置（使用正确的 API Key）
        await self.create_test_model_config(
            provider=settings.llm_provider,
            api_key=self._get_llm_api_key()
        )
        
        conversation_id = await self.create_test_conversation()

        # 发送AI对话请求
        chat_data = {
            "conversation_id": conversation_id,
            "message": "你好",
            "use_rag": False
        }
        response = await self.client.post(
            "/ai-chat/chat",
            json=chat_data,
            timeout=settings.llm_request_timeout
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "response" in data
        assert "conversation_id" in data
        assert "input_tokens" in data
        assert "output_tokens" in data
        assert "total_tokens" in data
        assert "model" in data
        assert data["conversation_id"] == conversation_id

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_ai_chat_with_rag(self):
        """测试使用RAG的AI对话"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        await self.create_test_model_config(
            provider=settings.llm_provider,
            api_key=self._get_llm_api_key()
        )
        
        conversation_id = await self.create_test_conversation()

        # 发送带RAG的对话请求
        chat_data = {
            "conversation_id": conversation_id,
            "message": "退货政策是什么？",
            "use_rag": True,
            "rag_top_k": 3
        }
        response = await self.client.post(
            "/ai-chat/chat",
            json=chat_data,
            timeout=settings.llm_request_timeout
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "response" in data
        assert data["used_rag"] is True

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_classify_intent(self):
        """测试意图分类"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        await self.create_test_model_config(provider=settings.llm_provider, api_key=self._get_llm_api_key())
        
        conversation_id = await self.create_test_conversation()

        # 意图分类请求
        response = await self.client.post(
            "/ai-chat/classify-intent",
            params={
                "conversation_id": conversation_id,
                "message": "我想退货"
            },
            timeout=settings.llm_request_timeout
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "intent" in data
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_extract_entities(self):
        """测试实体提取"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        await self.create_test_model_config(provider=settings.llm_provider, api_key=self._get_llm_api_key())
        
        conversation_id = await self.create_test_conversation()

        # 实体提取请求
        response = await self.client.post(
            "/ai-chat/extract-entities",
            params={
                "conversation_id": conversation_id,
                "message": "我的订单号是123456，想查询物流"
            },
            timeout=settings.llm_request_timeout
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "entities" in data
        assert "message" in data

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_get_conversation_summary(self):
        """测试获取对话摘要"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        await self.create_test_model_config(provider=settings.llm_provider, api_key=self._get_llm_api_key())
        
        conversation_id = await self.create_test_conversation()

        # 先进行几轮对话
        for message in ["你好", "我想查询订单", "谢谢"]:
            await self.client.post(
                "/ai-chat/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": message,
                    "use_rag": False
                },
                timeout=settings.llm_request_timeout
            )

        # 获取对话摘要
        response = await self.client.get(
            f"/ai-chat/conversation/{conversation_id}/summary",
            timeout=settings.llm_request_timeout
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "summary" in data or "stats" in data

    @pytest.mark.asyncio
    async def test_clear_conversation_memory(self):
        """测试清空对话记忆"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        conversation_id = await self.create_test_conversation()

        # 清空记忆
        response = await self.client.delete(
            f"/ai-chat/conversation/{conversation_id}/memory"
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "message" in data
        assert data["conversation_id"] == conversation_id

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_multiple_rounds_chat(self):
        """测试多轮对话"""
        # 创建租户和对话
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        await self.create_test_model_config(provider=settings.llm_provider, api_key=self._get_llm_api_key())
        
        conversation_id = await self.create_test_conversation()

        # 多轮对话
        messages = [
            "你好",
            "我想了解退货政策",
            "退货需要什么条件？",
        ]

        for message in messages:
            response = await self.client.post(
                "/ai-chat/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": message,
                    "use_rag": False
                },
                timeout=settings.llm_request_timeout
            )

            data = self.assert_success(response)
            assert "response" in data
