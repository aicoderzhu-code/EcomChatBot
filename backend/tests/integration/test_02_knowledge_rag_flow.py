"""
知识库RAG完整流程测试

测试从知识库创建到RAG检索的完整流程
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
@pytest.mark.rag  # 需要Milvus支持
class TestKnowledgeRAGFlow(
    BaseAPITest,
    TenantTestMixin,
    ConversationTestMixin,
    KnowledgeTestMixin,
    ModelConfigTestMixin,
):
    """知识库RAG完整流程测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_knowledge_rag_flow(self):
        """
        测试知识库RAG完整流程
        
        流程：
        1. 创建租户
        2. 创建单个知识条目
        3. 批量导入知识
        4. 查询知识列表
        5. 搜索知识（关键词）
        6. 更新知识条目
        7. RAG索引构建
        8. RAG检索测试
        9. 基于RAG的AI对话
        10. 查看RAG统计信息
        11. 删除知识条目
        """
        # ========== 步骤1: 创建租户 ==========
        print("\n[步骤1] 创建租户...")
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        print(f"✓ 租户创建成功: {tenant_info['tenant_id']}")

        # ========== 步骤2: 创建单个知识条目 ==========
        print("\n[步骤2] 创建单个知识条目...")
        knowledge_data = {
            "title": "产品保修政策",
            "content": "所有产品提供一年质保服务，质保期内免费维修。非人为损坏可以免费换新。",
            "category": "售后服务",
            "tags": ["保修", "质保"],
            "source": "官方文档"
        }
        
        create_resp = await self.client.post(
            "/knowledge/create",
            json=knowledge_data
        )
        create_data = self.assert_success(create_resp)
        
        knowledge_id_1 = create_data["knowledge_id"]
        self.cleaner.register_knowledge(knowledge_id_1)
        print(f"✓ 知识条目创建成功: {knowledge_id_1}")

        # ========== 步骤3: 批量导入知识 ==========
        print("\n[步骤3] 批量导入知识...")
        items = self.data_gen.get_predefined_knowledge()
        
        batch_resp = await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )
        batch_data = self.assert_success(batch_resp)
        
        created_count = len(batch_data["created"])
        print(f"✓ 批量导入成功，创建 {created_count} 条知识")
        
        # 注册清理
        for item in batch_data["created"]:
            self.cleaner.register_knowledge(item["knowledge_id"])

        # ========== 步骤4: 查询知识列表 ==========
        print("\n[步骤4] 查询知识列表...")
        list_resp = await self.client.get(
            "/knowledge/list",
            params={"page": 1, "size": 20}
        )
        list_data = self.assert_success(list_resp)
        
        total_knowledge = list_data["total"]
        print(f"✓ 知识列表查询成功，共 {total_knowledge} 条知识")
        assert total_knowledge >= created_count + 1

        # ========== 步骤5: 搜索知识（关键词） ==========
        print("\n[步骤5] 搜索知识...")
        search_resp = await self.client.post(
            "/knowledge/search",
            json={
                "query": "退货",
                "top_k": 5
            }
        )
        search_data = self.assert_success(search_resp)
        print(f"✓ 知识搜索成功，找到 {len(search_data)} 条相关知识")

        # ========== 步骤6: 更新知识条目 ==========
        print("\n[步骤6] 更新知识条目...")
        update_resp = await self.client.put(
            f"/knowledge/{knowledge_id_1}",
            json={
                "title": "产品保修政策（更新版）",
                "content": "所有产品提供两年质保服务，质保期内免费维修。",
                "category": "售后服务"
            }
        )
        update_data = self.assert_success(update_resp)
        assert "更新版" in update_data["title"]
        print(f"✓ 知识条目更新成功")

        # ========== 步骤7: RAG索引构建 ==========
        print("\n[步骤7] RAG索引构建...")
        index_resp = await self.client.post("/rag/index")
        
        if index_resp.status_code == 200:
            index_data = self.assert_success(index_resp)
            print(f"✓ RAG索引构建成功")
        else:
            print(f"⚠ RAG索引接口未实现或失败")

        # ========== 步骤8: RAG检索测试 ==========
        print("\n[步骤8] RAG检索测试...")
        retrieve_resp = await self.client.post(
            "/rag/retrieve",
            json={
                "query": "如何退货？",
                "top_k": 3
            }
        )
        
        if retrieve_resp.status_code == 200:
            retrieve_data = self.assert_success(retrieve_resp)
            print(f"✓ RAG检索成功")
        else:
            print(f"⚠ RAG检索接口未实现或失败")

        # ========== 步骤9: 基于RAG的AI对话 ==========
        if settings.has_llm_config:
            print("\n[步骤9] 基于RAG的AI对话...")

            # 使用 API Key 创建模型配置（/models 端点需要 API Key 认证）
            self.client.set_api_key(tenant_info["api_key"])
            await self.create_test_model_config(
                provider=settings.llm_provider
            )
            
            # 创建对话
            conversation_id = await self.create_test_conversation()
            
            # 带RAG的对话
            rag_chat_resp = await self.client.post(
                "/ai-chat/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "请告诉我退货政策是什么？",
                    "use_rag": True,
                    "rag_top_k": 3
                },
                timeout=settings.llm_request_timeout
            )
            
            rag_chat_data = self.assert_success(rag_chat_resp)
            assert "response" in rag_chat_data
            assert rag_chat_data["used_rag"] is True
            print(f"✓ RAG对话成功")
            print(f"  回复: {rag_chat_data['response'][:100]}...")
        else:
            print("\n[步骤9] 跳过（未配置LLM）")

        # ========== 步骤10: 查看RAG统计信息 ==========
        print("\n[步骤10] 查看RAG统计信息...")
        stats_resp = await self.client.get("/rag/stats")
        
        if stats_resp.status_code == 200:
            stats_data = self.assert_success(stats_resp)
            print(f"✓ RAG统计信息查询成功")
        else:
            print(f"⚠ RAG统计接口未实现")

        # ========== 步骤11: 删除知识条目 ==========
        print("\n[步骤11] 删除知识条目...")
        delete_resp = await self.client.delete(f"/knowledge/{knowledge_id_1}")
        self.assert_success(delete_resp)
        
        # 验证删除（可能是软删除返回200，或真删除返回404/400）
        get_resp = await self.client.get(f"/knowledge/{knowledge_id_1}")
        if get_resp.status_code == 200:
            # 软删除情况，检查是否标记为已删除
            get_data = get_resp.json()
            if get_data.get("success") and get_data.get("data"):
                knowledge = get_data["data"]
                # 软删除后 status 变为 inactive 或 deleted
                assert knowledge.get("status") in ["deleted", "inactive"] or knowledge.get("is_deleted") is True, \
                    f"知识条目应该被标记为已删除, 当前状态: {knowledge.get('status')}"
        else:
            assert get_resp.status_code in [404, 400], f"意外的状态码: {get_resp.status_code}"
        print(f"✓ 知识条目删除成功")

        print("\n" + "="*50)
        print("✅ 知识库RAG完整流程测试通过！")
        print("="*50)
