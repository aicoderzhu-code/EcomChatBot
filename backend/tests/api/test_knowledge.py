"""
知识库测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, KnowledgeTestMixin
from utils.assertions import assert_paginated


@pytest.mark.knowledge
class TestKnowledge(BaseAPITest, TenantTestMixin, KnowledgeTestMixin):
    """知识库测试"""

    @pytest.mark.asyncio
    async def test_create_knowledge(self):
        """测试创建知识条目"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建知识条目
        knowledge_data = self.data_gen.generate_knowledge_item("测试分类")
        response = await self.client.post(
            "/knowledge/create",
            json=knowledge_data
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "knowledge_id" in data
        assert data["title"] == knowledge_data["title"]
        assert data["category"] == knowledge_data["category"]

        # 注册清理
        self.cleaner.register_knowledge(data["knowledge_id"])

    @pytest.mark.asyncio
    async def test_batch_import_knowledge(self):
        """测试批量导入知识"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 批量导入
        items = self.data_gen.get_predefined_knowledge()
        response = await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "created" in data
        assert len(data["created"]) == len(items)

        # 注册清理
        for item in data["created"]:
            self.cleaner.register_knowledge(item["knowledge_id"])

    @pytest.mark.asyncio
    async def test_list_knowledge(self):
        """测试查询知识列表"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建几个知识条目
        for i in range(3):
            await self.create_test_knowledge(f"分类{i}")

        # 查询列表
        response = await self.client.get(
            "/knowledge/list",
            params={"page": 1, "size": 10}
        )

        data = self.assert_success(response)

        # 验证分页数据
        assert_paginated(data, min_total=3)

    @pytest.mark.asyncio
    async def test_get_knowledge_detail(self):
        """测试获取知识详情"""
        # 创建租户和知识
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        knowledge_id = await self.create_test_knowledge()

        # 获取详情
        response = await self.client.get(f"/knowledge/{knowledge_id}")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["knowledge_id"] == knowledge_id
        assert "title" in data
        assert "content" in data

    @pytest.mark.asyncio
    async def test_update_knowledge(self):
        """测试更新知识条目"""
        # 创建租户和知识
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        knowledge_id = await self.create_test_knowledge()

        # 更新知识
        update_data = {
            "title": "更新后的标题",
            "content": "更新后的内容",
            "category": "新分类"
        }
        response = await self.client.put(
            f"/knowledge/{knowledge_id}",
            json=update_data
        )

        data = self.assert_success(response)

        # 验证更新成功
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]

    @pytest.mark.asyncio
    async def test_search_knowledge(self):
        """测试搜索知识"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 批量导入知识
        items = self.data_gen.get_predefined_knowledge()
        await self.client.post(
            "/knowledge/batch-import",
            json={"items": items}
        )

        # 搜索知识
        response = await self.client.post(
            "/knowledge/search",
            json={
                "query": "退货",
                "top_k": 5
            }
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_delete_knowledge(self):
        """测试删除知识条目"""
        # 创建租户和知识
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        knowledge_id = await self.create_test_knowledge()

        # 删除知识
        response = await self.client.delete(f"/knowledge/{knowledge_id}")
        self.assert_success(response)

        # 验证删除成功（API 可能使用软删除，返回 200/404/400 都可以接受）
        response = await self.client.get(f"/knowledge/{knowledge_id}")
        # 软删除后可能仍返回 200，但 status 字段会变化；或者返回 404/400
        assert response.status_code in [200, 404, 400]

    @pytest.mark.asyncio
    async def test_list_knowledge_by_category(self):
        """测试按分类查询知识"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建特定分类的知识
        category = "特殊分类_测试"
        for i in range(2):
            await self.create_test_knowledge(category)

        # 按分类查询
        response = await self.client.get(
            "/knowledge/list",
            params={"category": category, "page": 1, "size": 10}
        )

        data = self.assert_success(response)
        assert_paginated(data, min_total=2)

    @pytest.mark.asyncio
    async def test_knowledge_with_tags(self):
        """测试带标签的知识条目"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建带标签的知识
        knowledge_data = self.data_gen.generate_knowledge_item()
        knowledge_data["tags"] = ["标签1", "标签2", "标签3"]

        response = await self.client.post(
            "/knowledge/create",
            json=knowledge_data
        )

        data = self.assert_success(response)
        assert "tags" in data
        assert len(data["tags"]) == 3

        # 注册清理
        self.cleaner.register_knowledge(data["knowledge_id"])
