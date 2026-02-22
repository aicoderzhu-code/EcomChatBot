"""
用户完整旅程测试

测试一个新用户从注册到使用的完整流程
"""
import pytest
from test_base import (
    BaseAPITest,
    TenantTestMixin,
    ConversationTestMixin,
    KnowledgeTestMixin,
    ModelConfigTestMixin,
)
from config import settings


@pytest.mark.integration
class TestUserJourney(
    BaseAPITest,
    TenantTestMixin,
    ConversationTestMixin,
    KnowledgeTestMixin,
    ModelConfigTestMixin,
):
    """用户完整旅程测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_user_journey(self):
        """
        测试用户完整旅程
        
        流程：
        1. 租户注册
        2. 租户登录
        3. 查看租户信息（API Key和JWT Token两种方式）
        4. 查看订阅信息
        5. 查看配额使用情况
        6. 创建模型配置
        7. 创建对话会话
        8. 发送消息
        9. AI对话
        10. 查看对话历史
        11. 获取对话摘要
        12. 关闭会话并评价
        13. 查看统计数据
        """
        # ========== 步骤1: 租户注册 ==========
        print("\n[步骤1] 租户注册...")
        tenant_data = self.data_gen.generate_tenant(settings.tenant_prefix)
        register_resp = await self.client.post(
            "/tenant/register",
            json=tenant_data
        )
        register_data = self.assert_success(register_resp)
        
        tenant_id = register_data["tenant_id"]
        api_key = register_data["api_key"]
        
        assert tenant_id
        assert api_key.startswith("eck_")
        
        self.cleaner.register_tenant(tenant_id)
        print(f"✓ 租户注册成功: {tenant_id}")

        # ========== 步骤2: 租户登录 ==========
        print("\n[步骤2] 租户登录...")
        login_resp = await self.client.post(
            "/tenant/login",
            json={
                "email": tenant_data["contact_email"],
                "password": tenant_data["password"]
            }
        )
        login_data = self.assert_success(login_resp)
        
        jwt_token = login_data["access_token"]
        assert jwt_token
        print(f"✓ 登录成功，获取JWT Token")

        # ========== 步骤3: 查看租户信息 ==========
        print("\n[步骤3] 查看租户信息...")
        
        # 使用API Key查看
        self.client.set_api_key(api_key)
        info_resp = await self.client.get("/tenant/info")
        info_data = self.assert_success(info_resp)
        assert info_data["tenant_id"] == tenant_id
        print(f"✓ API Key认证成功")
        
        # 使用JWT Token查看
        self.client.clear_auth()
        self.client.set_jwt_token(jwt_token)
        info_resp2 = await self.client.get("/tenant/info-token")
        info_data2 = self.assert_success(info_resp2)
        assert info_data2["tenant_id"] == tenant_id
        print(f"✓ JWT Token认证成功")
        
        # 后续使用API Key
        self.client.clear_auth()
        self.client.set_api_key(api_key)

        # ========== 步骤4: 查看订阅信息 ==========
        print("\n[步骤4] 查看订阅信息...")
        sub_resp = await self.client.get("/tenant/subscription")
        sub_data = self.assert_success(sub_resp)
        assert "plan_type" in sub_data
        print(f"✓ 当前套餐: {sub_data['plan_type']}")

        # ========== 步骤5: 查看配额 ==========
        print("\n[步骤5] 查看配额使用情况...")
        quota_resp = await self.client.get("/tenant/quota")
        quota_data = self.assert_success(quota_resp)
        # 字段名与 QuotaUsageResponse 一致
        assert "concurrent" in quota_data
        print(f"✓ 配额查询成功")

        # ========== 步骤6: 创建模型配置 ==========
        if settings.has_llm_config:
            print("\n[步骤6] 创建模型配置...")
            # /models 端点需要 API Key 认证，确保使用 API Key
            self.client.clear_auth()
            self.client.set_api_key(api_key)

            config_data = self.data_gen.generate_model_config(
                provider=settings.llm_provider,
                api_key=(
                    settings.zhipuai_api_key
                    if settings.llm_provider == "zhipuai"
                    else settings.openai_api_key
                )
            )

            model_resp = await self.client.post("/models", json=config_data)
            model_data = self.assert_success(model_resp)

            config_id = model_data["id"]
            self.cleaner.register_model_config(config_id)
            print(f"✓ 模型配置创建成功: {config_id}")
        else:
            print("\n[步骤6] 跳过（未配置LLM）")

        # ========== 步骤7: 创建对话会话 ==========
        print("\n[步骤7] 创建对话会话...")
        user_data = self.data_gen.generate_user()
        conv_resp = await self.client.post(
            "/conversation/create",
            json=user_data
        )
        conv_data = self.assert_success(conv_resp)
        
        conversation_id = conv_data["conversation_id"]
        self.cleaner.register_conversation(conversation_id)
        print(f"✓ 对话创建成功: {conversation_id}")

        # ========== 步骤8: 发送消息 ==========
        print("\n[步骤8] 发送消息...")
        msg_resp = await self.client.post(
            f"/conversation/{conversation_id}/messages",
            json={"content": "你好，这是测试消息"}
        )
        msg_data = self.assert_success(msg_resp)
        assert "message_id" in msg_data
        print(f"✓ 消息发送成功")

        # ========== 步骤9: AI对话 ==========
        if settings.has_llm_config:
            print("\n[步骤9] AI对话...")
            chat_resp = await self.client.post(
                "/ai-chat/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "你好，请介绍一下自己",
                    "use_rag": False
                },
                timeout=settings.llm_request_timeout
            )
            chat_data = self.assert_success(chat_resp)
            assert "response" in chat_data
            print(f"✓ AI对话成功，回复: {chat_data['response'][:50]}...")
        else:
            print("\n[步骤9] 跳过（未配置LLM）")

        # ========== 步骤10: 查看对话历史 ==========
        print("\n[步骤10] 查看对话历史...")
        history_resp = await self.client.get(
            f"/conversation/{conversation_id}/messages"
        )
        history_data = self.assert_success(history_resp)
        assert isinstance(history_data, list)
        assert len(history_data) >= 1
        print(f"✓ 对话历史查询成功，共 {len(history_data)} 条消息")

        # ========== 步骤11: 获取对话摘要 ==========
        if settings.has_llm_config:
            print("\n[步骤11] 获取对话摘要...")
            summary_resp = await self.client.get(
                f"/ai-chat/conversation/{conversation_id}/summary",
                timeout=settings.llm_request_timeout
            )
            if summary_resp.status_code == 200:
                summary_data = self.assert_success(summary_resp)
                print(f"✓ 对话摘要获取成功")
        else:
            print("\n[步骤11] 跳过（未配置LLM）")

        # ========== 步骤12: 关闭会话并评价 ==========
        print("\n[步骤12] 关闭会话并评价...")
        close_resp = await self.client.put(
            f"/conversation/{conversation_id}",
            json={
                "status": "closed",
                "satisfaction_score": 5,
                "feedback": "测试评价：服务很好"
            }
        )
        close_data = self.assert_success(close_resp)
        assert close_data["status"] == "closed"
        print(f"✓ 会话已关闭，评分: 5")

        # ========== 步骤13: 查看统计数据 ==========
        print("\n[步骤13] 查看统计数据...")
        
        # 对话统计
        stat_resp = await self.client.get("/monitor/conversations")
        stat_data = self.assert_success(stat_resp)
        print(f"✓ 统计数据查询成功")

        # 满意度统计
        sat_resp = await self.client.get("/monitor/satisfaction")
        if sat_resp.status_code == 200:
            sat_data = self.assert_success(sat_resp)
            print(f"✓ 满意度统计查询成功")

        print("\n" + "="*50)
        print("✅ 用户完整旅程测试通过！")
        print("="*50)
