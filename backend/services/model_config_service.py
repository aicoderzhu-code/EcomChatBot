"""
LLM模型配置管理服务
"""
from typing import Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.model_config import ModelConfig, LLMProvider
from core.exceptions import AppException


class ModelConfigService:
    """LLM模型配置管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def create_model_config(
        self,
        provider: str,
        model_name: str,
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float | None = None,
        use_case: str | None = None,
        is_default: bool = False,
        priority: int = 0,
        advanced_config: dict | None = None
    ) -> ModelConfig:
        """
        创建模型配置

        Args:
            provider: LLM提供商
            model_name: 模型名称
            api_key: API密钥
            api_base: API基础URL
            temperature: 温度参数
            max_tokens: 最大Token数
            top_p: Top-P参数
            use_case: 使用场景
            is_default: 是否为默认模型
            priority: 优先级
            advanced_config: 高级配置

        Returns:
            ModelConfig
        """
        # 验证提供商
        try:
            LLMProvider(provider)
        except ValueError:
            raise AppException(f"无效的LLM提供商: {provider}")

        # 如果设置为默认，取消其他默认配置
        if is_default:
            await self._clear_default_config(use_case)

        config = ModelConfig(
            tenant_id=self.tenant_id,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            use_case=use_case,
            is_default=is_default,
            priority=priority,
            advanced_config=advanced_config
        )

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def _clear_default_config(self, use_case: str | None = None):
        """清除默认配置"""
        conditions = [
            ModelConfig.tenant_id == self.tenant_id,
            ModelConfig.is_default == True
        ]

        if use_case:
            conditions.append(ModelConfig.use_case == use_case)

        stmt = select(ModelConfig).where(*conditions)
        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        for config in configs:
            config.is_default = False

        await self.db.commit()

    async def get_model_config(self, config_id: int) -> ModelConfig:
        """获取模型配置"""
        stmt = select(ModelConfig).where(
            and_(
                ModelConfig.id == config_id,
                ModelConfig.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise AppException("模型配置不存在")

        return config

    async def list_model_configs(
        self,
        provider: str | None = None,
        use_case: str | None = None,
        is_active: bool | None = None
    ) -> list[ModelConfig]:
        """列出模型配置"""
        conditions = [ModelConfig.tenant_id == self.tenant_id]

        if provider:
            conditions.append(ModelConfig.provider == provider)
        if use_case:
            conditions.append(ModelConfig.use_case == use_case)
        if is_active is not None:
            conditions.append(ModelConfig.is_active == is_active)

        stmt = select(ModelConfig).where(*conditions).order_by(
            ModelConfig.priority.desc(),
            ModelConfig.created_at.desc()
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_model_config(
        self,
        config_id: int,
        **kwargs
    ) -> ModelConfig:
        """更新模型配置"""
        config = await self.get_model_config(config_id)

        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                if key == "is_default" and value is True:
                    # 取消其他默认配置
                    await self._clear_default_config(config.use_case)
                setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def delete_model_config(self, config_id: int) -> bool:
        """删除模型配置"""
        config = await self.get_model_config(config_id)
        await self.db.delete(config)
        await self.db.commit()
        return True

    async def get_default_model(
        self,
        use_case: str | None = None
    ) -> ModelConfig | None:
        """
        获取默认模型配置

        Args:
            use_case: 使用场景（可选）

        Returns:
            ModelConfig | None
        """
        conditions = [
            ModelConfig.tenant_id == self.tenant_id,
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ]

        if use_case:
            # 优先查找匹配use_case的默认配置
            conditions.append(ModelConfig.use_case == use_case)
        else:
            # 如果没有指定use_case，查找use_case为None的默认配置
            conditions.append(ModelConfig.use_case == None)

        stmt = select(ModelConfig).where(*conditions)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def select_model_for_intent(
        self,
        intent: str,
        use_case: str | None = None
    ) -> ModelConfig | None:
        """
        根据意图选择合适的模型

        路由策略：
        1. 优先使用use_case匹配的默认模型
        2. 如果没有，根据intent类型选择模型
        3. 按优先级排序，选择最高优先级的可用模型
        4. 考虑负载均衡（选择调用次数少的模型）

        Args:
            intent: 用户意图
            use_case: 使用场景

        Returns:
            ModelConfig | None
        """
        # 1. 尝试获取use_case的默认模型
        if use_case:
            default_config = await self.get_default_model(use_case)
            if default_config:
                return default_config

        # 2. 根据意图选择use_case
        intent_use_case = self._map_intent_to_use_case(intent)

        if intent_use_case:
            intent_config = await self.get_default_model(intent_use_case)
            if intent_config:
                return intent_config

        # 3. 按优先级选择可用模型
        conditions = [
            ModelConfig.tenant_id == self.tenant_id,
            ModelConfig.is_active == True
        ]

        if use_case:
            conditions.append(
                or_(
                    ModelConfig.use_case == use_case,
                    ModelConfig.use_case == None
                )
            )

        stmt = select(ModelConfig).where(*conditions).order_by(
            ModelConfig.priority.desc(),
            ModelConfig.total_calls.asc()  # 负载均衡：选择调用次数少的
        )
        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        if configs:
            return configs[0]

        # 4. 如果没有找到，返回None
        return None

    def _map_intent_to_use_case(self, intent: str) -> str | None:
        """
        将意图映射到使用场景

        Args:
            intent: 意图

        Returns:
            使用场景
        """
        # 意图到使用场景的映射
        intent_mapping = {
            # 对话相关
            "greeting": "dialogue",
            "chitchat": "dialogue",
            "complaint": "dialogue",

            # 业务咨询
            "order_query": "rag",
            "product_consult": "rag",
            "after_sales": "rag",

            # RAG相关
            "knowledge_query": "rag",
            "faq": "rag",

            # 翻译
            "translation": "translation",

            # 摘要
            "summarization": "summarization",
        }

        return intent_mapping.get(intent)

    async def record_model_usage(
        self,
        config_id: int,
        success: bool = True,
        tokens: int = 0
    ):
        """
        记录模型使用情况

        Args:
            config_id: 配置ID
            success: 是否成功
            tokens: Token消耗
        """
        config = await self.get_model_config(config_id)

        config.total_calls += 1
        if success:
            config.success_calls += 1
        else:
            config.failed_calls += 1

        config.total_tokens += tokens

        await self.db.commit()
