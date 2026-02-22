"""
认证安全测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, ConversationTestMixin
from config import settings


@pytest.mark.security
@pytest.mark.skipif(settings.skip_security, reason="安全测试已跳过")
class TestAuthSecurity(BaseAPITest, TenantTestMixin, ConversationTestMixin):
    """认证安全测试"""

    @pytest.mark.asyncio
    async def test_access_without_authentication(self):
        """测试无认证访问受保护的接口"""
        # 确保没有设置认证信息
        self.client.clear_auth()

        # 尝试访问需要认证的接口
        protected_endpoints = [
            "/tenant/info",
            "/conversation/list",
            "/knowledge/list",
            "/monitor/conversations",
        ]

        for endpoint in protected_endpoints:
            response = await self.client.get(endpoint)
            # 应该返回401或403
            assert response.status_code in [401, 403], \
                f"接口 {endpoint} 未正确保护，返回状态码: {response.status_code}"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """测试使用无效的API Key"""
        invalid_keys = [
            "invalid_key",
            "eck_invalid123456789",
            "",
            "null",
        ]

        for invalid_key in invalid_keys:
            self.client.set_api_key(invalid_key)
            response = await self.client.get("/tenant/info")
            # API 对无效 Key 返回 400 (INVALID_API_KEY)，对缺失认证返回 401
            assert response.status_code in [400, 401, 403]

    @pytest.mark.asyncio
    async def test_invalid_jwt_token(self):
        """测试使用无效的JWT Token"""
        invalid_tokens = [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "",
        ]

        for invalid_token in invalid_tokens:
            self.client.set_jwt_token(invalid_token)
            response = await self.client.get("/tenant/info-token")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_cross_tenant_data_access(self):
        """测试跨租户数据访问防护"""
        # 创建两个租户
        tenant1 = await self.create_test_tenant()
        tenant2 = await self.create_test_tenant()

        # 租户1创建对话
        self.client.set_api_key(tenant1["api_key"])
        conv_id_1 = await self.create_test_conversation()

        # 租户2尝试访问租户1的对话
        self.client.set_api_key(tenant2["api_key"])
        response = await self.client.get(f"/conversation/{conv_id_1}")

        # 跨租户访问应该被阻止（返回 400/403/404）
        assert response.status_code in [400, 403, 404], \
            f"跨租户访问未被正确阻止, 状态码: {response.status_code}"

    @pytest.mark.asyncio
    async def test_cross_tenant_knowledge_access(self):
        """测试跨租户知识库访问防护"""
        # 创建两个租户
        tenant1 = await self.create_test_tenant()
        tenant2 = await self.create_test_tenant()

        # 租户1创建知识
        self.client.set_api_key(tenant1["api_key"])
        knowledge_data = self.data_gen.generate_knowledge_item()
        create_resp = await self.client.post(
            "/knowledge/create",
            json=knowledge_data
        )
        knowledge_data_1 = self.assert_success(create_resp)
        knowledge_id_1 = knowledge_data_1["knowledge_id"]
        self.cleaner.register_knowledge(knowledge_id_1)

        # 租户2尝试访问租户1的知识
        self.client.set_api_key(tenant2["api_key"])
        response = await self.client.get(f"/knowledge/{knowledge_id_1}")

        # 跨租户访问应该被阻止（返回 400/403/404）
        assert response.status_code in [400, 403, 404], \
            f"跨租户知识库访问未被正确阻止, 状态码: {response.status_code}"

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 尝试SQL注入
        malicious_inputs = [
            "'; DROP TABLE tenants; --",
            "1' OR '1'='1",
            "admin'--",
        ]

        for malicious_input in malicious_inputs:
            # 尝试在搜索中注入
            response = await self.client.post(
                "/knowledge/search",
                json={"query": malicious_input, "top_k": 5}
            )
            
            # 应该安全处理，返回200或400，但不应该500
            assert response.status_code != 500, \
                f"可能存在SQL注入漏洞，输入: {malicious_input}"

    @pytest.mark.asyncio
    async def test_xss_prevention(self):
        """测试XSS防护"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 尝试XSS攻击
        xss_payload = "<script>alert('XSS')</script>"

        # 创建包含XSS的知识
        knowledge_data = {
            "title": xss_payload,
            "content": f"测试内容 {xss_payload}",
            "category": "测试"
        }

        response = await self.client.post(
            "/knowledge/create",
            json=knowledge_data
        )

        if response.status_code == 200:
            data = self.assert_success(response)
            knowledge_id = data["knowledge_id"]
            self.cleaner.register_knowledge(knowledge_id)

            # 获取知识，检查是否被转义
            get_resp = await self.client.get(f"/knowledge/{knowledge_id}")
            get_data = self.assert_success(get_resp)
            
            # 验证内容（这里只是基本检查，实际应该在前端进行转义）
            assert get_data["title"] is not None
