"""
并发对话测试
"""
import pytest
import asyncio
import time
from test_base import BaseAPITest, TenantTestMixin, ConversationTestMixin, ModelConfigTestMixin
from config import settings


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.skipif(settings.skip_performance, reason="性能测试已跳过")
class TestConcurrentChat(
    BaseAPITest,
    TenantTestMixin,
    ConversationTestMixin,
    ModelConfigTestMixin,
):
    """并发对话测试"""

    @pytest.mark.asyncio
    async def test_concurrent_conversations(self):
        """测试并发创建对话"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 并发创建对话
        concurrent_count = min(10, settings.max_concurrent)
        print(f"\n并发创建 {concurrent_count} 个对话...")

        start_time = time.time()

        async def create_conv(index):
            user_data = self.data_gen.generate_user(index)
            response = await self.client.post(
                "/conversation/create",
                json=user_data
            )
            return response

        # 并发执行
        tasks = [create_conv(i) for i in range(concurrent_count)]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        elapsed = end_time - start_time

        # 验证所有请求都成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        
        print(f"✓ 创建成功: {success_count}/{concurrent_count}")
        print(f"✓ 总耗时: {elapsed:.2f}秒")
        print(f"✓ 平均耗时: {elapsed/concurrent_count:.3f}秒/请求")
        print(f"✓ QPS: {concurrent_count/elapsed:.2f}")

        # 注册清理
        for response in responses:
            if response.status_code == 200:
                data = response.json()["data"]
                self.cleaner.register_conversation(data["conversation_id"])

        # 性能断言
        assert success_count >= concurrent_count * 0.9  # 至少90%成功
        assert elapsed / concurrent_count < 1.0  # 平均响应时间 < 1秒

    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.has_llm_config, reason="未配置LLM")
    async def test_concurrent_ai_chat(self):
        """测试并发AI对话"""
        # 创建租户和模型配置
        tenant_info = await self.create_test_tenant()

        # 使用 API Key 创建模型配置（/models 端点需要 API Key 认证）
        self.client.set_api_key(tenant_info["api_key"])

        await self.create_test_model_config(provider=settings.llm_provider)

        # 创建对话
        conversation_id = await self.create_test_conversation()

        # 并发AI对话
        concurrent_count = min(5, settings.max_concurrent // 2)
        print(f"\n并发执行 {concurrent_count} 次AI对话...")

        messages = ["你好", "介绍一下", "谢谢", "再见", "了解"]

        async def ai_chat(index):
            response = await self.client.post(
                "/ai-chat/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": messages[index % len(messages)],
                    "use_rag": False
                },
                timeout=settings.llm_request_timeout
            )
            return response

        start_time = time.time()
        tasks = [ai_chat(i) for i in range(concurrent_count)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        elapsed = end_time - start_time

        # 统计成功数
        success_count = sum(
            1 for r in responses 
            if not isinstance(r, Exception) and r.status_code == 200
        )

        print(f"✓ 对话成功: {success_count}/{concurrent_count}")
        print(f"✓ 总耗时: {elapsed:.2f}秒")
        print(f"✓ 平均耗时: {elapsed/concurrent_count:.3f}秒/请求")

        # LLM调用可能有限流，允许部分失败
        assert success_count >= concurrent_count * 0.7  # 至少70%成功
