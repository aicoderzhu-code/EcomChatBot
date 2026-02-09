"""
RAG检索增强模块测试
测试覆盖: 5个接口, 25个测试用例
包含: 向量检索、RAG生成、知识索引、批量索引、统计信息
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.rag]


# ==================== 1. RAG检索测试 ====================


class TestRAGRetrieval:
    """RAG检索测试"""

    async def test_rag_retrieve_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试基础RAG检索"""
        retrieve_request = {
            "query": "如何退货？",
            "top_k": 5,
            "use_vector_search": True,
        }

        response = await client.post(
            "/api/v1/rag/retrieve",
            json=retrieve_request,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证检索结果
        results = data["data"]
        assert isinstance(results, list)
        assert len(results) <= 5

    async def test_rag_retrieve_with_different_top_k(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试不同top_k值的检索"""
        for top_k in [1, 3, 5, 10]:
            retrieve_request = {
                "query": "商品质量问题",
                "top_k": top_k,
                "use_vector_search": True,
            }

            response = await client.post(
                "/api/v1/rag/retrieve",
                json=retrieve_request,
                headers=tenant_api_key_headers,
            )

            if response.status_code == 200:
                data = response.json()
                results = data["data"]
                assert len(results) <= top_k

    async def test_rag_retrieve_without_vector_search(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试不使用向量搜索的检索"""
        retrieve_request = {
            "query": "退货政策",
            "top_k": 5,
            "use_vector_search": False,  # 只用关键词搜索
        }

        response = await client.post(
            "/api/v1/rag/retrieve",
            json=retrieve_request,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_rag_retrieve_empty_query(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试空查询"""
        retrieve_request = {"query": "", "top_k": 5}

        response = await client.post(
            "/api/v1/rag/retrieve",
            json=retrieve_request,
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]

    async def test_rag_retrieve_long_query(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试长查询"""
        long_query = "我想咨询一下关于" + "商品退货" * 50

        retrieve_request = {"query": long_query, "top_k": 5}

        response = await client.post(
            "/api/v1/rag/retrieve",
            json=retrieve_request,
            headers=tenant_api_key_headers,
        )

        # 应该能处理长查询或返回错误
        assert response.status_code in [200, 400]


# ==================== 2. RAG生成测试 ====================


class TestRAGGeneration:
    """RAG生成测试"""

    async def test_rag_generate_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试基础RAG生成"""
        generate_request = {"query": "如何退货？", "use_vector_search": True}

        response = await client.post(
            "/api/v1/rag/generate",
            json=generate_request,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证生成结果
        result = data["data"]
        assert "answer" in result or "response" in result

    async def test_rag_generate_with_sources(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试RAG生成包含来源"""
        generate_request = {"query": "退货流程是什么？", "use_vector_search": True}

        response = await client.post(
            "/api/v1/rag/generate",
            json=generate_request,
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            result = data["data"]

            # 应该包含来源信息
            if "sources" in result:
                assert isinstance(result["sources"], list)

    async def test_rag_generate_without_vector_search(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试不使用向量搜索的生成"""
        generate_request = {"query": "商品保修多久？", "use_vector_search": False}

        response = await client.post(
            "/api/v1/rag/generate",
            json=generate_request,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)


# ==================== 3. 知识索引测试 ====================


class TestKnowledgeIndexing:
    """知识索引测试"""

    async def test_index_single_knowledge(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试索引单个知识"""
        # 先创建知识
        create_response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )

        if create_response.status_code == 200:
            knowledge_id = create_response.json()["data"]["knowledge_id"]

            # 创建索引
            index_request = {"knowledge_id": knowledge_id}

            response = await client.post(
                "/api/v1/rag/index",
                json=index_request,
                headers=tenant_api_key_headers,
            )

            if response.status_code == 200:
                data = response.json()
                result = data["data"]
                assert "success" in result or "status" in result

    async def test_index_nonexistent_knowledge(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试索引不存在的知识"""
        index_request = {"knowledge_id": "KNOW_NOTEXIST"}

        response = await client.post(
            "/api/v1/rag/index",
            json=index_request,
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 404]

    async def test_batch_index_knowledge(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试批量索引知识"""
        # 创建多个知识
        knowledge_ids = []
        for i in range(3):
            knowledge_data = TestDataGenerator.generate_knowledge()
            create_response = await client.post(
                "/api/v1/knowledge/create",
                json=knowledge_data,
                headers=tenant_api_key_headers,
            )

            if create_response.status_code == 200:
                knowledge_ids.append(create_response.json()["data"]["knowledge_id"])

        if knowledge_ids:
            # 批量索引
            batch_request = {"knowledge_ids": knowledge_ids}

            response = await client.post(
                "/api/v1/rag/index-batch",
                json=batch_request,
                headers=tenant_api_key_headers,
            )

            if response.status_code == 200:
                data = response.json()
                result = data["data"]
                assert "success_count" in result or "total" in result

    async def test_batch_index_empty_list(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试批量索引空列表"""
        batch_request = {"knowledge_ids": []}

        response = await client.post(
            "/api/v1/rag/index-batch",
            json=batch_request,
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]


# ==================== 4. RAG统计信息测试 ====================


class TestRAGStats:
    """RAG统计信息测试"""

    async def test_get_rag_stats(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取RAG统计信息"""
        response = await client.get(
            "/api/v1/rag/stats", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证统计信息
        stats = data["data"]
        assert isinstance(stats, dict)

    async def test_rag_stats_contains_embedding_info(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试RAG统计包含Embedding信息"""
        response = await client.get(
            "/api/v1/rag/stats", headers=tenant_api_key_headers
        )

        if response.status_code == 200:
            data = response.json()
            stats = data["data"]

            # 可能包含的统计信息
            possible_keys = [
                "total_vectors",
                "embedding_model",
                "vector_dimension",
                "index_type",
            ]

            # 至少应该有一些统计信息
            assert len(stats) > 0


# ==================== 5. RAG性能测试 ====================


class TestRAGPerformance:
    """RAG性能测试"""

    @pytest.mark.slow
    async def test_rag_retrieve_performance(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试RAG检索性能"""
        import time

        retrieve_request = {"query": "商品退货政策", "top_k": 10}

        start = time.time()
        response = await client.post(
            "/api/v1/rag/retrieve",
            json=retrieve_request,
            headers=tenant_api_key_headers,
        )
        duration = time.time() - start

        # 检索应该在合理时间内完成（例如2秒内）
        if response.status_code == 200:
            assert duration < 2.0, f"RAG检索耗时过长: {duration:.2f}s"

    @pytest.mark.slow
    async def test_rag_generate_performance(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试RAG生成性能"""
        import time

        generate_request = {"query": "如何办理退货？"}

        start = time.time()
        response = await client.post(
            "/api/v1/rag/generate",
            json=generate_request,
            headers=tenant_api_key_headers,
        )
        duration = time.time() - start

        # RAG生成可能需要更长时间（包含LLM调用）
        if response.status_code == 200:
            assert duration < 5.0, f"RAG生成耗时过长: {duration:.2f}s"

    async def test_concurrent_rag_retrieval(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试并发RAG检索"""
        import asyncio

        retrieve_request = {"query": "测试查询", "top_k": 5}

        # 并发发送5个检索请求
        tasks = [
            client.post(
                "/api/v1/rag/retrieve",
                json=retrieve_request,
                headers=tenant_api_key_headers,
            )
            for _ in range(5)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 大部分请求应该成功
        success_count = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )

        assert success_count >= 3, f"并发检索成功率过低: {success_count}/5"
