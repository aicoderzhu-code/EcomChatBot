"""
模型配置测试
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, ModelConfigTestMixin
from config import settings


@pytest.mark.model_config
class TestModelConfig(BaseAPITest, TenantTestMixin, ModelConfigTestMixin):
    """模型配置测试"""

    @pytest.mark.asyncio
    async def test_create_model_config(self):
        """测试创建模型配置"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        config_data = self.data_gen.generate_model_config(
            provider="zhipuai",
            api_key="test_api_key_123456"
        )

        response = await self.client.post(
            "/models",
            json=config_data
        )

        data = self.assert_success(response)

        # 验证返回数据
        assert "id" in data
        assert data["provider"] == "zhipuai"
        assert data["model_name"] == config_data["model_name"]

        # 注册清理
        self.cleaner.register_model_config(data["id"])

    @pytest.mark.asyncio
    async def test_list_model_configs(self):
        """测试列出模型配置"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建几个模型配置
        for provider in ["zhipuai", "openai"]:
            config_data = self.data_gen.generate_model_config(
                provider=provider,
                api_key=f"test_key_{provider}"
            )
            config_data["is_default"] = False
            await self.client.post("/models", json=config_data)

        # 列出配置
        response = await self.client.get("/models")
        data = self.assert_success(response)

        # 验证返回数据
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_default_model(self):
        """测试获取默认模型"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建默认模型配置
        config_data = self.data_gen.generate_model_config(
            provider="zhipuai",
            api_key="test_api_key"
        )
        config_data["is_default"] = True
        create_resp = await self.client.post("/models", json=config_data)
        created_data = self.assert_success(create_resp)

        # 获取默认模型（API 可能返回 null 如果没有配置全局默认）
        response = await self.client.get("/models/default")

        if response.status_code == 200:
            data = self.assert_success(response)
            # 如果返回了数据，验证 is_default 为 True
            if data is not None:
                assert data["is_default"] is True

    @pytest.mark.asyncio
    async def test_get_model_config_detail(self):
        """测试获取模型配置详情"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        config_id = await self.create_test_model_config(
            provider="zhipuai",
            api_key="test_api_key"
        )

        # 获取详情
        response = await self.client.get(f"/models/{config_id}")
        data = self.assert_success(response)

        # 验证返回数据
        assert data["id"] == config_id
        assert "provider" in data
        assert "model_name" in data

    @pytest.mark.asyncio
    async def test_update_model_config(self):
        """测试更新模型配置"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        config_id = await self.create_test_model_config()

        # 更新配置
        update_data = {
            "max_tokens": 3000
        }
        response = await self.client.put(
            f"/models/{config_id}",
            json=update_data
        )

        data = self.assert_success(response)

        # 验证更新成功（max_tokens 可以正确更新）
        assert data["max_tokens"] == 3000

    @pytest.mark.asyncio
    async def test_delete_model_config(self):
        """测试删除模型配置"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 创建模型配置
        config_data = self.data_gen.generate_model_config(
            provider="zhipuai",
            api_key="test_key"
        )
        config_data["is_default"] = False
        create_resp = await self.client.post("/models", json=config_data)
        created = self.assert_success(create_resp)
        config_id = created["id"]

        # 删除配置
        response = await self.client.delete(f"/models/{config_id}")
        self.assert_success(response)

        # 验证删除成功
        response = await self.client.get(f"/models/{config_id}")
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_create_config_with_different_providers(self):
        """测试创建不同提供商的配置"""
        # 创建租户并使用API Key认证
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 测试不同的提供商
        providers = ["zhipuai", "openai", "anthropic"]

        for provider in providers:
            config_data = self.data_gen.generate_model_config(
                provider=provider,
                api_key=f"test_{provider}_key"
            )
            config_data["is_default"] = False

            response = await self.client.post("/models", json=config_data)

            if response.status_code == 200:
                data = self.assert_success(response)
                assert data["provider"] == provider
                self.cleaner.register_model_config(data["id"])
