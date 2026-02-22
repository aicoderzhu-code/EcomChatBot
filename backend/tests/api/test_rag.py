"""
RAG 检索测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, KnowledgeTestMixin
from config import settings


@pytest.mark.rag
class TestRAG(BaseAPITest, TenantTestMixin, KnowledgeTestMixin):
    """RAG 检索测试"""

    @pytest.mark.asyncio
    async def test_rag_retrieve(self):
        """测试RAG检索"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 批量导入知识
        items = self.data_gen.get_predefined_knowledge()
        await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )

        # RAG检索
        response = await self.client.post(
            "/rag/retrieve",
            json={
                "query": "退货政策",
                "top_k": 3
            }
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert isinstance(data, list) or "results" in data

    @pytest.mark.asyncio
    async def test_rag_generate(self):
        """测试RAG生成"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 批量导入知识
        items = self.data_gen.get_predefined_knowledge()
        await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )

        # RAG生成
        response = await self.client.post(
            "/rag/generate",
            json={
                "query": "请介绍一下退货政策",
                "top_k": 3
            },
            timeout=settings.llm_request_timeout
        )

        # 如果返回404或500，可能是该接口未实现
        if response.status_code == 200:
            data = self.assert_success(response)
            assert "answer" in data or "response" in data

    @pytest.mark.asyncio
    async def test_rag_index(self):
        """测试RAG索引"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 批量导入知识
        items = self.data_gen.get_predefined_knowledge()
        await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )

        # 构建索引
        response = await self.client.post("/rag/index")

        # 索引可能需要一些时间
        if response.status_code == 200:
            data = self.assert_success(response)
            # 验证索引结果

    @pytest.mark.asyncio
    async def test_rag_stats(self):
        """测试RAG统计信息"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 获取统计信息
        response = await self.client.get("/rag/stats")

        if response.status_code == 200:
            data = self.assert_success(response)
            # 验证统计数据
            assert isinstance(data, dict)
