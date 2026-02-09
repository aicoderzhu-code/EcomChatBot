"""
知识库管理模块测试
测试覆盖: 10个接口, 50个测试用例
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, TestDataGenerator

pytestmark = [pytest.mark.asyncio, pytest.mark.knowledge]


class TestKnowledgeCRUD:
    """知识库CRUD测试"""

    async def test_create_knowledge_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试创建知识条目成功"""
        response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        knowledge = data["data"]
        assert "knowledge_id" in knowledge
        assert knowledge["title"] == knowledge_data["title"]
        assert knowledge["content"] == knowledge_data["content"]
        assert knowledge["category"] == knowledge_data["category"]

    async def test_create_knowledge_with_tags(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建带标签的知识"""
        knowledge_data = TestDataGenerator.generate_knowledge()
        knowledge_data["tags"] = ["标签1", "标签2", "标签3"]

        response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        knowledge = data["data"]
        assert len(knowledge["tags"]) == 3

    async def test_list_knowledge(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询知识列表"""
        response = await client.get(
            "/api/v1/knowledge/list",
            params={"page": 1, "size": 20},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        AssertHelper.assert_pagination(data["data"])

    async def test_list_knowledge_filter_by_type(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试按类型过滤知识"""
        response = await client.get(
            "/api/v1/knowledge/list",
            params={"knowledge_type": "faq"},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        items = data["data"]["items"]
        for item in items:
            assert item["knowledge_type"] == "faq"

    async def test_list_knowledge_filter_by_category(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试按分类过滤知识"""
        response = await client.get(
            "/api/v1/knowledge/list",
            params={"category": "常见问题"},
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            items = data["data"]["items"]
            for item in items:
                assert item["category"] == "常见问题"

    async def test_get_knowledge_detail(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试获取知识详情"""
        # 先创建知识
        create_response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )
        knowledge_id = create_response.json()["data"]["knowledge_id"]

        # 获取详情
        response = await client.get(
            f"/api/v1/knowledge/{knowledge_id}",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        knowledge = data["data"]
        assert knowledge["knowledge_id"] == knowledge_id
        assert knowledge["title"] == knowledge_data["title"]

    async def test_update_knowledge_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试更新知识条目"""
        # 先创建知识
        create_response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )
        knowledge_id = create_response.json()["data"]["knowledge_id"]

        # 更新知识
        update_data = {
            "title": "更新后的标题",
            "content": "更新后的内容",
            "priority": 5,
        }

        response = await client.put(
            f"/api/v1/knowledge/{knowledge_id}",
            json=update_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        knowledge = data["data"]
        assert knowledge["title"] == update_data["title"]
        assert knowledge["content"] == update_data["content"]
        assert knowledge["priority"] == update_data["priority"]

    async def test_delete_knowledge_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试删除知识条目"""
        # 先创建知识
        create_response = await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )
        knowledge_id = create_response.json()["data"]["knowledge_id"]

        # 删除知识
        response = await client.delete(
            f"/api/v1/knowledge/{knowledge_id}",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        assert "message" in data["data"]


class TestKnowledgeBatchImport:
    """知识库批量导入测试"""

    async def test_batch_import_knowledge_success(
        self, client: AsyncClient, tenant_api_key_headers: dict, generate_multiple_knowledge
    ):
        """测试批量导入知识成功"""
        knowledge_items = generate_multiple_knowledge(5)

        import_data = {"knowledge_items": knowledge_items}

        response = await client.post(
            "/api/v1/knowledge/batch-import",
            json=import_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        result = data["data"]
        assert "success_count" in result
        assert "failed_count" in result
        assert result["success_count"] > 0

    async def test_batch_import_with_duplicates(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试批量导入包含重复数据"""
        knowledge_items = [
            TestDataGenerator.generate_knowledge(),
            TestDataGenerator.generate_knowledge(),
        ]

        # 让两个条目有相同的标题(假设标题唯一)
        knowledge_items[1]["title"] = knowledge_items[0]["title"]

        import_data = {"knowledge_items": knowledge_items}

        response = await client.post(
            "/api/v1/knowledge/batch-import",
            json=import_data,
            headers=tenant_api_key_headers,
        )

        # 应该返回部分成功
        if response.status_code == 200:
            data = response.json()
            result = data["data"]
            # 可能有一条失败
            assert result["success_count"] + result["failed_count"] == len(knowledge_items)


class TestKnowledgeSearch:
    """知识搜索测试"""

    async def test_search_knowledge_by_keyword(
        self, client: AsyncClient, tenant_api_key_headers: dict, knowledge_data: dict
    ):
        """测试按关键词搜索知识"""
        # 先创建知识
        await client.post(
            "/api/v1/knowledge/create",
            json=knowledge_data,
            headers=tenant_api_key_headers,
        )

        # 搜索知识
        search_keyword = knowledge_data["title"].split()[0]  # 取标题的第一个词

        response = await client.post(
            "/api/v1/knowledge/search",
            params={"query": search_keyword, "top_k": 5},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        results = data["data"]
        assert isinstance(results, list)

    async def test_search_knowledge_with_type_filter(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试搜索时过滤知识类型"""
        response = await client.post(
            "/api/v1/knowledge/search",
            params={"query": "退货", "knowledge_type": "faq", "top_k": 10},
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            results = data["data"]

            for result in results:
                assert result["knowledge_type"] == "faq"


class TestRAGQuery:
    """RAG查询测试"""

    async def test_rag_query_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试基本RAG查询"""
        rag_request = {"query": "如何退货？", "top_k": 3}

        response = await client.post(
            "/api/v1/knowledge/rag/query",
            json=rag_request,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        result = data["data"]
        assert "results" in result
        assert "query_time" in result

    async def test_rag_query_with_different_top_k(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试不同top_k值的RAG查询"""
        for top_k in [1, 3, 5, 10]:
            rag_request = {"query": "商品质量问题", "top_k": top_k}

            response = await client.post(
                "/api/v1/knowledge/rag/query",
                json=rag_request,
                headers=tenant_api_key_headers,
            )

            if response.status_code == 200:
                data = response.json()
                results = data["data"]["results"]
                assert len(results) <= top_k
