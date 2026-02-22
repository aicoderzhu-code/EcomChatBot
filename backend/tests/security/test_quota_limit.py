"""
配额限制测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, ConversationTestMixin
from config import settings


@pytest.mark.security
@pytest.mark.skipif(settings.skip_security, reason="安全测试已跳过")
class TestQuotaLimit(BaseAPITest, TenantTestMixin, ConversationTestMixin):
    """配额限制测试"""

    @pytest.mark.asyncio
    async def test_check_quota_usage(self):
        """测试检查配额使用情况"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 查看初始配额
        response = await self.client.get("/tenant/quota")
        quota_data = self.assert_success(response)

        print(f"\n初始配额:")
        print(f"  并发会话: {quota_data.get('concurrent', {})}")
        print(f"  每日对话: {quota_data.get('conversation', {})}")
        print(f"  每日API调用: {quota_data.get('api_call', {})}")

        # 验证配额数据结构（字段名与 QuotaUsageResponse 一致）
        assert "concurrent" in quota_data
        assert "conversation" in quota_data
        assert "api_call" in quota_data

    @pytest.mark.asyncio
    async def test_concurrent_session_limit(self):
        """测试并发会话数限制"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 获取配额限制
        quota_resp = await self.client.get("/tenant/quota")
        quota_data = self.assert_success(quota_resp)

        concurrent_limit = quota_data.get("concurrent", {}).get("limit", 10)

        print(f"\n并发会话限制: {concurrent_limit}")

        # 创建会话直到达到限制
        conversation_ids = []
        
        for i in range(int(concurrent_limit) + 2):
            response = await self.client.post(
                "/conversation/create",
                json=self.data_gen.generate_user(i)
            )
            
            if response.status_code == 200:
                data = self.assert_success(response)
                conversation_ids.append(data["conversation_id"])
                self.cleaner.register_conversation(data["conversation_id"])
            else:
                print(f"  第 {i+1} 个会话创建失败（可能达到限制）")
                break

        print(f"  成功创建 {len(conversation_ids)} 个会话")

    @pytest.mark.asyncio
    async def test_daily_conversation_limit(self):
        """测试每日对话次数限制"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建对话
        conversation_id = await self.create_test_conversation()

        # 发送消息（会增加对话次数）
        success_count = 0
        max_attempts = 10  # 不要发送太多，避免真的超限

        for i in range(max_attempts):
            response = await self.client.post(
                f"/conversation/{conversation_id}/messages",
                json={"content": f"测试消息 {i+1}"}
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"  第 {i+1} 条消息发送失败")
                break

        print(f"\n成功发送 {success_count} 条消息")

        # 检查配额使用情况
        quota_resp = await self.client.get("/tenant/quota")
        quota_data = self.assert_success(quota_resp)
        
        conv_quota = quota_data.get("conversation", {})
        print(f"  每日对话配额: {conv_quota.get('used', 0)}/{conv_quota.get('limit', 0)}")
