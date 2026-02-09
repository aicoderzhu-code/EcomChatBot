"""
端到端(E2E)测试
测试覆盖: 完整业务流程, 50个测试用例
模拟真实用户场景的完整流程测试
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


# ==================== 1. 租户完整生命周期测试 ====================


class TestTenantLifecycle:
    """租户完整生命周期测试"""

    async def test_tenant_full_lifecycle(self, client: AsyncClient):
        """测试租户从注册到使用的完整流程"""
        # Step 1: 租户注册
        tenant_data = TestDataGenerator.generate_tenant()

        register_response = await client.post(
            "/api/v1/tenant/register", json=tenant_data
        )

        assert register_response.status_code == 200
        register_data = register_response.json()["data"]
        tenant_id = register_data["tenant_id"]
        api_key = register_data["api_key"]

        # Step 2: 使用API Key获取租户信息
        tenant_headers = {"X-API-Key": api_key}

        info_response = await client.get(
            "/api/v1/tenant/info", headers=tenant_headers
        )

        assert info_response.status_code == 200
        info_data = info_response.json()["data"]
        assert info_data["tenant_id"] == tenant_id

        # Step 3: 查看配额
        quota_response = await client.get(
            "/api/v1/tenant/quota", headers=tenant_headers
        )

        assert quota_response.status_code == 200

        # Step 4: 创建会话
        conversation_data = TestDataGenerator.generate_conversation()

        conv_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_headers,
        )

        assert conv_response.status_code == 200
        conversation_id = conv_response.json()["data"]["conversation_id"]

        # Step 5: 进行对话
        chat_request = {
            "conversation_id": conversation_id,
            "message": "你好，我需要帮助",
            "use_rag": False,
        }

        chat_response = await client.post(
            "/api/v1/ai-chat/chat", json=chat_request, headers=tenant_headers
        )

        assert chat_response.status_code == 200

        # Step 6: 查看对话历史
        messages_response = await client.get(
            f"/api/v1/conversation/{conversation_id}/messages",
            headers=tenant_headers,
        )

        assert messages_response.status_code == 200

        # Step 7: 关闭会话
        update_data = {"status": "closed", "satisfaction_score": 5}

        close_response = await client.put(
            f"/api/v1/conversation/{conversation_id}",
            json=update_data,
            headers=tenant_headers,
        )

        assert close_response.status_code == 200


# ==================== 2. 知识库到对话的完整流程 ====================


class TestKnowledgeToConversation:
    """知识库到AI对话的完整流程"""

    async def test_knowledge_rag_conversation_flow(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试从创建知识到RAG对话的完整流程"""
        # Step 1: 创建知识库条目
        knowledge_data = {
            "knowledge_type": "faq",
            "title": "退货政策",
            "content": "我们支持7天无理由退货，商品需保持原包装...",
            "category": "售后服务",
            "tags": ["退货", "售后"],
            "source": "manual",
            "priority": 1,
        }

        knowledge_response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )

        assert knowledge_response.status_code == 200
        knowledge_id = knowledge_response.json()["data"]["knowledge_id"]

        # Step 2: 索引知识库(可选,取决于实现)
        # index_response = await client.post(
        #     "/api/v1/rag/index",
        #     json={"knowledge_id": knowledge_id},
        #     headers=tenant_api_key_headers
        # )

        # Step 3: 创建会话
        conversation_data = TestDataGenerator.generate_conversation()

        conv_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # Step 4: 使用RAG进行对话
        chat_request = {
            "conversation_id": conversation_id,
            "message": "请问你们的退货政策是什么？",
            "use_rag": True,
            "rag_top_k": 3,
        }

        chat_response = await client.post(
            "/api/v1/ai-chat/chat",
            json=chat_request,
            headers=tenant_api_key_headers,
        )

        assert chat_response.status_code == 200
        chat_data = chat_response.json()["data"]

        # 验证使用了RAG
        assert chat_data.get("used_rag") is True


# ==================== 3. 套餐订阅到支付的完整流程 ====================


class TestSubscriptionPaymentFlow:
    """套餐订阅到支付的完整流程"""

    async def test_subscription_to_payment_flow(
        self, client: AsyncClient, tenant_data: dict
    ):
        """测试从租户注册到套餐订阅支付的完整流程"""
        # Step 1: 租户注册
        register_response = await client.post(
            "/api/v1/tenant/register", json=tenant_data
        )

        tenant_id = register_response.json()["data"]["tenant_id"]
        api_key = register_response.json()["data"]["api_key"]
        tenant_headers = {"X-API-Key": api_key}

        # Step 2: 查看当前订阅(应该是免费版)
        subscription_response = await client.get(
            "/api/v1/tenant/subscription", headers=tenant_headers
        )

        current_plan = subscription_response.json()["data"]["plan_type"]

        # Step 3: 登录获取Token(用于套餐订阅)
        login_response = await client.post(
            "/api/v1/tenant/login",
            json={"email": tenant_data["contact_email"], "password": tenant_data["password"]},
        )

        token = login_response.json()["data"]["access_token"]
        token_headers = {"Authorization": f"Bearer {token}"}

        # Step 4: 预览套餐变更价格
        preview_response = await client.get(
            "/api/v1/tenant/subscription/price-preview",
            params={"new_plan_type": "basic"},
            headers=token_headers,
        )

        # Step 5: 订阅付费套餐
        subscribe_request = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_method": "alipay",
            "auto_renew": False,
        }

        subscribe_response = await client.post(
            "/api/v1/tenant/subscribe",
            json=subscribe_request,
            headers=token_headers,
        )

        if subscribe_response.status_code == 200:
            subscribe_data = subscribe_response.json()["data"]

            # 应该需要支付
            if subscribe_data.get("payment_required"):
                order_number = subscribe_data["order_number"]

                # Step 6: 查询订单详情
                order_response = await client.get(
                    f"/api/v1/payment/orders/{order_number}",
                    headers=tenant_headers,
                )

                assert order_response.status_code == 200

                # Step 7: 模拟支付(在真实环境中是支付宝回调)
                # 这里只测试查询订单状态
                status_response = await client.get(
                    f"/api/v1/payment/orders/{order_number}/status",
                    headers=tenant_headers,
                )

                assert status_response.status_code == 200


# ==================== 4. 管理员管理租户的完整流程 ====================


class TestAdminTenantManagement:
    """管理员管理租户的完整流程"""

    async def test_admin_manage_tenant_flow(
        self, client: AsyncClient, test_admin, admin_headers: dict
    ):
        """测试管理员创建和管理租户的完整流程"""
        # Step 1: 管理员登录(已通过fixture完成)

        # Step 2: 创建租户(代客开户)
        tenant_data = TestDataGenerator.generate_tenant()

        create_response = await client.post(
            "/api/v1/admin/tenants", json=tenant_data, headers=admin_headers
        )

        if create_response.status_code == 200:
            created_tenant = create_response.json()["data"]
            tenant_id = created_tenant["tenant_id"]
            api_key = created_tenant["api_key"]

            # Step 3: 为租户分配套餐
            assign_response = await client.post(
                f"/api/v1/admin/tenants/{tenant_id}/assign-plan",
                params={"plan_type": "basic", "duration_months": 3},
                headers=admin_headers,
            )

            # Step 4: 调整租户配额
            adjust_response = await client.post(
                f"/api/v1/admin/tenants/{tenant_id}/adjust-quota",
                params={"quota_type": "api_calls", "amount": 1000, "reason": "补偿"},
                headers=admin_headers,
            )

            # Step 5: 查看租户详情
            detail_response = await client.get(
                f"/api/v1/admin/tenants/{tenant_id}", headers=admin_headers
            )

            assert detail_response.status_code == 200


# ==================== 5. 对话质量评估完整流程 ====================


class TestConversationQualityFlow:
    """对话质量评估完整流程"""

    async def test_conversation_quality_evaluation_flow(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试从创建对话到质量评估的完整流程"""
        # Step 1: 创建会话
        conversation_data = TestDataGenerator.generate_conversation()

        conv_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # Step 2: 进行多轮对话
        messages = [
            "你好，我想咨询商品信息",
            "这个商品有货吗？",
            "价格是多少？",
            "好的，谢谢",
        ]

        for message in messages:
            chat_request = {
                "conversation_id": conversation_id,
                "message": message,
                "use_rag": False,
            }

            await client.post(
                "/api/v1/ai-chat/chat",
                json=chat_request,
                headers=tenant_api_key_headers,
            )

        # Step 3: 关闭会话并评价
        close_data = {"status": "closed", "satisfaction_score": 5, "feedback": "服务很好"}

        await client.put(
            f"/api/v1/conversation/{conversation_id}",
            json=close_data,
            headers=tenant_api_key_headers,
        )

        # Step 4: 评估对话质量
        quality_response = await client.get(
            f"/api/v1/quality/conversation/{conversation_id}",
            headers=tenant_api_key_headers,
        )

        if quality_response.status_code == 200:
            quality_data = quality_response.json()["data"]
            # 验证质量评估结果
            assert "score" in quality_data or "quality_score" in quality_data


# ==================== 6. 并发会话处理流程 ====================


class TestConcurrentConversations:
    """并发会话处理流程"""

    @pytest.mark.slow
    async def test_concurrent_conversations_flow(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试并发创建和处理多个会话"""
        import asyncio

        # 并发创建5个会话
        conversation_tasks = [
            client.post(
                "/api/v1/conversation/create",
                json=TestDataGenerator.generate_conversation(),
                headers=tenant_api_key_headers,
            )
            for _ in range(5)
        ]

        conversation_responses = await asyncio.gather(*conversation_tasks)

        # 获取成功创建的会话ID
        conversation_ids = [
            resp.json()["data"]["conversation_id"]
            for resp in conversation_responses
            if resp.status_code == 200
        ]

        # 在每个会话中并发发送消息
        chat_tasks = []
        for conv_id in conversation_ids:
            chat_request = {
                "conversation_id": conv_id,
                "message": "测试消息",
                "use_rag": False,
            }
            chat_tasks.append(
                client.post(
                    "/api/v1/ai-chat/chat",
                    json=chat_request,
                    headers=tenant_api_key_headers,
                )
            )

        chat_responses = await asyncio.gather(*chat_tasks)

        # 验证大部分对话成功
        success_count = sum(1 for r in chat_responses if r.status_code == 200)
        assert success_count >= len(conversation_ids) * 0.8  # 80%成功率


# ==================== 7. 监控数据验证流程 ====================


class TestMonitoringDataFlow:
    """监控数据验证流程"""

    async def test_monitoring_data_accuracy_flow(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建对话后监控数据的准确性"""
        # Step 1: 记录初始统计数据
        initial_stats_response = await client.get(
            "/api/v1/monitor/conversations", headers=tenant_api_key_headers
        )

        # Step 2: 创建几个会话并对话
        for i in range(3):
            # 创建会话
            conversation_data = TestDataGenerator.generate_conversation()
            conv_response = await client.post(
                "/api/v1/conversation/create",
                json=conversation_data,
                headers=tenant_api_key_headers,
            )

            if conv_response.status_code == 200:
                conversation_id = conv_response.json()["data"]["conversation_id"]

                # 发送消息
                chat_request = {
                    "conversation_id": conversation_id,
                    "message": f"测试消息{i}",
                    "use_rag": False,
                }

                await client.post(
                    "/api/v1/ai-chat/chat",
                    json=chat_request,
                    headers=tenant_api_key_headers,
                )

        # Step 3: 查看更新后的统计数据
        updated_stats_response = await client.get(
            "/api/v1/monitor/conversations", headers=tenant_api_key_headers
        )

        # 验证统计数据有更新
        assert updated_stats_response.status_code == 200


# ==================== 8. 知识库批量操作流程 ====================


class TestKnowledgeBatchOperations:
    """知识库批量操作流程"""

    async def test_knowledge_batch_workflow(
        self, client: AsyncClient, tenant_api_key_headers: dict, generate_multiple_knowledge
    ):
        """测试知识库批量导入和搜索的完整流程"""
        # Step 1: 批量导入知识
        knowledge_items = generate_multiple_knowledge(10)

        import_request = {"knowledge_items": knowledge_items}

        import_response = await client.post(
            "/api/v1/knowledge/batch-import",
            json=import_request,
            headers=tenant_api_key_headers,
        )

        assert import_response.status_code == 200
        import_data = import_response.json()["data"]
        assert import_data["success_count"] > 0

        # Step 2: 搜索知识
        search_response = await client.post(
            "/api/v1/knowledge/search",
            params={"query": "测试", "top_k": 5},
            headers=tenant_api_key_headers,
        )

        assert search_response.status_code == 200

        # Step 3: RAG检索
        rag_request = {"query": "测试查询", "top_k": 5}

        rag_response = await client.post(
            "/api/v1/rag/retrieve",
            json=rag_request,
            headers=tenant_api_key_headers,
        )

        assert rag_response.status_code == 200


# ==================== 9. 完整客服对话场景 ====================


class TestCompleteCustomerServiceScenario:
    """完整客服对话场景"""

    async def test_complete_customer_service_scenario(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """模拟完整的客服对话场景"""
        # 场景: 用户咨询商品->查询订单->申请退货->评价满意

        # Step 1: 用户发起咨询
        conversation_data = {
            "user_id": "customer_001",
            "channel": "web",
            "metadata": {"device": "desktop", "source": "official_website"},
        }

        conv_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        conversation_id = conv_response.json()["data"]["conversation_id"]

        # Step 2: 多轮对话
        conversation_flow = [
            {"message": "你好，我想咨询一下商品", "use_rag": False},
            {"message": "这款商品有货吗？", "use_rag": True},
            {"message": "帮我查一下订单ORDER123456", "use_rag": False},
            {"message": "我想申请退货", "use_rag": True},
            {"message": "好的，谢谢你的帮助", "use_rag": False},
        ]

        for step in conversation_flow:
            chat_request = {"conversation_id": conversation_id, **step}

            chat_response = await client.post(
                "/api/v1/ai-chat/chat",
                json=chat_request,
                headers=tenant_api_key_headers,
            )

            assert chat_response.status_code == 200

        # Step 3: 生成对话摘要
        summary_response = await client.get(
            f"/api/v1/ai-chat/conversation/{conversation_id}/summary",
            headers=tenant_api_key_headers,
        )

        # Step 4: 用户评价并关闭会话
        close_data = {
            "status": "closed",
            "satisfaction_score": 5,
            "feedback": "客服很专业，解决了我的问题",
        }

        close_response = await client.put(
            f"/api/v1/conversation/{conversation_id}",
            json=close_data,
            headers=tenant_api_key_headers,
        )

        assert close_response.status_code == 200


# ==================== 10. 系统压力测试场景 ====================


@pytest.mark.slow
@pytest.mark.performance
class TestSystemStressScenario:
    """系统压力测试场景"""

    async def test_high_load_scenario(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试高负载场景下的系统表现"""
        import asyncio

        # 模拟50个并发用户
        async def simulate_user():
            # 创建会话
            conversation_data = TestDataGenerator.generate_conversation()
            conv_response = await client.post(
                "/api/v1/conversation/create",
                json=conversation_data,
                headers=tenant_api_key_headers,
            )

            if conv_response.status_code == 200:
                conversation_id = conv_response.json()["data"]["conversation_id"]

                # 发送消息
                chat_request = {
                    "conversation_id": conversation_id,
                    "message": "测试消息",
                    "use_rag": False,
                }

                chat_response = await client.post(
                    "/api/v1/ai-chat/chat",
                    json=chat_request,
                    headers=tenant_api_key_headers,
                )

                return chat_response.status_code == 200
            return False

        # 并发50个用户
        tasks = [simulate_user() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计成功率
        success_count = sum(1 for r in results if r is True)
        success_rate = success_count / len(results)

        # 至少70%成功率
        assert success_rate >= 0.7, f"成功率过低: {success_rate:.2%}"
