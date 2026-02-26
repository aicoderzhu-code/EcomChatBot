"""
LLM模型路由器

支持:
- 基于意图的模型选择
- 租户偏好配置
- 健康检查和故障转移
- 负载均衡
"""
import logging
import random
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .adapters import (
    LLMAdapter,
    LLMConfig,
    LLMResponse,
    LLMProvider,
    StreamChunk,
    LLMError,
    OpenAIAdapter,
)

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """路由策略"""
    PRIORITY = "priority"       # 按优先级选择
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"           # 随机
    LEAST_LATENCY = "least_latency"  # 最低延迟
    COST_OPTIMIZED = "cost_optimized"  # 成本优化


class IntentCategory(str, Enum):
    """意图类别"""
    GENERAL = "general"           # 通用对话
    CODING = "coding"             # 代码相关
    CREATIVE = "creative"         # 创意写作
    ANALYSIS = "analysis"         # 分析推理
    CUSTOMER_SERVICE = "customer_service"  # 客服对话
    KNOWLEDGE_QA = "knowledge_qa"  # 知识问答


@dataclass
class ProviderHealth:
    """提供商健康状态"""
    is_healthy: bool = True
    last_check: datetime = field(default_factory=datetime.now)
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None

    def record_success(self, latency_ms: float):
        """记录成功请求"""
        self.is_healthy = True
        self.consecutive_failures = 0
        # 滑动平均延迟
        self.avg_latency_ms = (self.avg_latency_ms * 0.8) + (latency_ms * 0.2)
        self.last_check = datetime.now()

    def record_failure(self, error: str):
        """记录失败请求"""
        self.consecutive_failures += 1
        self.last_error = error
        self.last_check = datetime.now()
        # 连续失败3次标记为不健康
        if self.consecutive_failures >= 3:
            self.is_healthy = False


@dataclass
class ProviderConfig:
    """提供商配置"""
    provider: LLMProvider
    priority: int = 0  # 优先级，数字越小优先级越高
    weight: float = 1.0  # 权重，用于负载均衡
    enabled: bool = True
    models: List[str] = field(default_factory=list)  # 可用模型
    cost_per_1k_tokens: float = 0.0  # 每1000 token成本


@dataclass
class TenantPreferences:
    """租户偏好配置"""
    tenant_id: str
    preferred_provider: Optional[LLMProvider] = None
    preferred_model: Optional[str] = None
    fallback_providers: List[LLMProvider] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.PRIORITY
    max_retries: int = 3
    intent_model_mapping: Dict[IntentCategory, str] = field(default_factory=dict)


class ModelRouter:
    """
    模型路由器

    负责根据意图、租户偏好、健康状态等选择最合适的LLM提供商和模型
    """

    # 默认意图-模型映射
    DEFAULT_INTENT_MODELS = {
        IntentCategory.GENERAL: "gpt-4o-mini",
        IntentCategory.CODING: "gpt-4o",
        IntentCategory.CREATIVE: "gpt-4o",
        IntentCategory.ANALYSIS: "gpt-4o",
        IntentCategory.CUSTOMER_SERVICE: "gpt-4o-mini",
        IntentCategory.KNOWLEDGE_QA: "gpt-4o-mini",
    }

    # 模型到提供商的映射
    MODEL_PROVIDER_MAP = {
        # OpenAI
        "gpt-4o": LLMProvider.OPENAI,
        "gpt-4o-mini": LLMProvider.OPENAI,
        "gpt-4-turbo": LLMProvider.OPENAI,
        "gpt-4": LLMProvider.OPENAI,
        "gpt-3.5-turbo": LLMProvider.OPENAI,
    }

    # 默认故障转移顺序
    DEFAULT_FALLBACK_ORDER = [
        LLMProvider.OPENAI,
    ]

    def __init__(self):
        """初始化路由器"""
        self._adapters: Dict[LLMProvider, LLMAdapter] = {}
        self._health_status: Dict[LLMProvider, ProviderHealth] = {}
        self._provider_configs: Dict[LLMProvider, ProviderConfig] = {}
        self._tenant_preferences: Dict[str, TenantPreferences] = {}
        self._round_robin_index = 0
        self._initialized = False

    def register_adapter(
        self,
        provider: LLMProvider,
        adapter: LLMAdapter,
        config: Optional[ProviderConfig] = None
    ):
        """
        注册LLM适配器

        Args:
            provider: 提供商标识
            adapter: 适配器实例
            config: 提供商配置
        """
        self._adapters[provider] = adapter
        self._health_status[provider] = ProviderHealth()
        if config:
            self._provider_configs[provider] = config
        else:
            self._provider_configs[provider] = ProviderConfig(
                provider=provider,
                models=adapter.supported_models
            )
        logger.info(f"Registered LLM adapter: {provider.value}")

    def set_tenant_preferences(self, preferences: TenantPreferences):
        """设置租户偏好"""
        self._tenant_preferences[preferences.tenant_id] = preferences
        logger.info(f"Set preferences for tenant: {preferences.tenant_id}")

    def get_tenant_preferences(self, tenant_id: str) -> TenantPreferences:
        """获取租户偏好"""
        return self._tenant_preferences.get(
            tenant_id,
            TenantPreferences(tenant_id=tenant_id)
        )

    async def initialize(
        self,
        openai_api_key: Optional[str] = None,
    ):
        """
        初始化路由器，注册所有可用的适配器

        Args:
            openai_api_key: OpenAI API密钥
        """
        if openai_api_key:
            try:
                adapter = OpenAIAdapter(api_key=openai_api_key)
                self.register_adapter(
                    LLMProvider.OPENAI,
                    adapter,
                    ProviderConfig(
                        provider=LLMProvider.OPENAI,
                        priority=1,
                        models=adapter.supported_models,
                        cost_per_1k_tokens=0.01,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI adapter: {e}")

        self._initialized = True
        logger.info(f"Router initialized with {len(self._adapters)} providers")

    def get_adapter(self, provider: LLMProvider) -> Optional[LLMAdapter]:
        """获取指定提供商的适配器"""
        return self._adapters.get(provider)

    def get_available_providers(self) -> List[LLMProvider]:
        """获取所有可用的提供商"""
        return [
            provider for provider, config in self._provider_configs.items()
            if config.enabled and self._health_status[provider].is_healthy
        ]

    def select_model_for_intent(
        self,
        intent: IntentCategory,
        tenant_id: Optional[str] = None
    ) -> Tuple[str, LLMProvider]:
        """
        根据意图选择模型

        Args:
            intent: 意图类别
            tenant_id: 租户ID（可选）

        Returns:
            (模型名称, 提供商)
        """
        # 优先使用租户自定义映射
        if tenant_id:
            prefs = self.get_tenant_preferences(tenant_id)
            if intent in prefs.intent_model_mapping:
                model = prefs.intent_model_mapping[intent]
                provider = self.MODEL_PROVIDER_MAP.get(model)
                if provider and provider in self._adapters:
                    return model, provider

        # 使用默认映射
        model = self.DEFAULT_INTENT_MODELS.get(intent, "gpt-4o-mini")
        provider = self.MODEL_PROVIDER_MAP.get(model, LLMProvider.OPENAI)

        # 检查提供商是否可用
        if provider not in self._adapters or not self._health_status[provider].is_healthy:
            # 尝试故障转移
            for fallback in self.DEFAULT_FALLBACK_ORDER:
                if fallback in self._adapters and self._health_status[fallback].is_healthy:
                    adapter = self._adapters[fallback]
                    return adapter.get_default_model(), fallback

        return model, provider

    def select_provider(
        self,
        tenant_id: Optional[str] = None,
        required_model: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None
    ) -> Tuple[LLMProvider, LLMAdapter]:
        """
        选择提供商

        Args:
            tenant_id: 租户ID
            required_model: 必须的模型（如果指定则选择支持该模型的提供商）
            strategy: 路由策略

        Returns:
            (提供商, 适配器)
        """
        # 获取租户偏好
        prefs = self.get_tenant_preferences(tenant_id) if tenant_id else None
        strategy = strategy or (prefs.strategy if prefs else RoutingStrategy.PRIORITY)

        # 如果指定了模型，直接选择对应提供商
        if required_model and required_model in self.MODEL_PROVIDER_MAP:
            provider = self.MODEL_PROVIDER_MAP[required_model]
            if provider in self._adapters:
                return provider, self._adapters[provider]

        # 获取可用提供商
        available = self.get_available_providers()
        if not available:
            raise LLMError("No available LLM providers")

        # 如果有租户首选提供商且可用
        if prefs and prefs.preferred_provider in available:
            provider = prefs.preferred_provider
            return provider, self._adapters[provider]

        # 根据策略选择
        if strategy == RoutingStrategy.PRIORITY:
            # 按优先级排序
            sorted_providers = sorted(
                available,
                key=lambda p: self._provider_configs[p].priority
            )
            provider = sorted_providers[0]

        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # 轮询
            self._round_robin_index = (self._round_robin_index + 1) % len(available)
            provider = available[self._round_robin_index]

        elif strategy == RoutingStrategy.RANDOM:
            # 随机选择（支持权重）
            weights = [self._provider_configs[p].weight for p in available]
            provider = random.choices(available, weights=weights, k=1)[0]

        elif strategy == RoutingStrategy.LEAST_LATENCY:
            # 最低延迟
            provider = min(
                available,
                key=lambda p: self._health_status[p].avg_latency_ms
            )

        elif strategy == RoutingStrategy.COST_OPTIMIZED:
            # 成本优化
            provider = min(
                available,
                key=lambda p: self._provider_configs[p].cost_per_1k_tokens
            )

        else:
            provider = available[0]

        return provider, self._adapters[provider]

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig,
        tenant_id: Optional[str] = None,
        intent: Optional[IntentCategory] = None
    ) -> LLMResponse:
        """
        生成回复（带故障转移）

        Args:
            messages: 消息列表
            config: LLM配置
            tenant_id: 租户ID
            intent: 意图类别

        Returns:
            LLMResponse
        """
        prefs = self.get_tenant_preferences(tenant_id) if tenant_id else None
        max_retries = prefs.max_retries if prefs else 3

        # 根据意图选择模型（如果未指定模型）
        if not config.model and intent:
            model, _ = self.select_model_for_intent(intent, tenant_id)
            config.model = model

        # 构建尝试顺序
        if config.model and config.model in self.MODEL_PROVIDER_MAP:
            primary_provider = self.MODEL_PROVIDER_MAP[config.model]
            providers_to_try = [primary_provider]
        else:
            provider, _ = self.select_provider(tenant_id, config.model)
            providers_to_try = [provider]

        # 添加故障转移提供商
        fallback_order = (prefs.fallback_providers if prefs else []) or self.DEFAULT_FALLBACK_ORDER
        for fb in fallback_order:
            if fb not in providers_to_try and fb in self._adapters:
                providers_to_try.append(fb)

        last_error = None
        for attempt, provider in enumerate(providers_to_try[:max_retries]):
            if provider not in self._adapters:
                continue

            adapter = self._adapters[provider]
            health = self._health_status[provider]

            # 跳过不健康的提供商（除非是最后的尝试）
            if not health.is_healthy and attempt < len(providers_to_try) - 1:
                logger.warning(f"Skipping unhealthy provider: {provider.value}")
                continue

            try:
                start_time = datetime.now()

                # 如果切换了提供商，可能需要调整模型
                if config.model and config.model not in adapter.supported_models:
                    original_model = config.model
                    config.model = adapter.get_default_model()
                    logger.info(f"Model {original_model} not supported by {provider.value}, using {config.model}")

                response = await adapter.generate(messages, config)

                # 记录成功
                latency = (datetime.now() - start_time).total_seconds() * 1000
                health.record_success(latency)

                return response

            except Exception as e:
                last_error = e
                health.record_failure(str(e))
                logger.warning(f"LLM request failed for {provider.value}: {e}")

                # 如果是认证错误，不重试这个提供商
                if "authentication" in str(e).lower() or "401" in str(e):
                    continue

        # 所有尝试都失败
        raise LLMError(
            f"All LLM providers failed. Last error: {last_error}",
            retryable=False
        )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig,
        tenant_id: Optional[str] = None,
        intent: Optional[IntentCategory] = None
    ):
        """
        流式生成回复

        与generate类似，但返回流式响应
        """
        prefs = self.get_tenant_preferences(tenant_id) if tenant_id else None

        # 根据意图选择模型
        if not config.model and intent:
            model, _ = self.select_model_for_intent(intent, tenant_id)
            config.model = model

        # 选择提供商
        provider, adapter = self.select_provider(tenant_id, config.model)

        # 调整模型
        if config.model and config.model not in adapter.supported_models:
            config.model = adapter.get_default_model()

        try:
            async for chunk in adapter.stream_generate(messages, config):
                yield chunk
            self._health_status[provider].record_success(0)
        except Exception as e:
            self._health_status[provider].record_failure(str(e))
            raise

    async def health_check_all(self) -> Dict[LLMProvider, bool]:
        """
        检查所有提供商的健康状态

        Returns:
            提供商健康状态映射
        """
        results = {}

        async def check_provider(provider: LLMProvider):
            adapter = self._adapters[provider]
            try:
                is_healthy = await adapter.health_check()
                self._health_status[provider].is_healthy = is_healthy
                results[provider] = is_healthy
            except Exception as e:
                self._health_status[provider].record_failure(str(e))
                results[provider] = False

        # 并发检查所有提供商
        await asyncio.gather(
            *[check_provider(p) for p in self._adapters.keys()],
            return_exceptions=True
        )

        return results

    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有提供商的健康状态"""
        return {
            provider.value: {
                "is_healthy": health.is_healthy,
                "last_check": health.last_check.isoformat(),
                "consecutive_failures": health.consecutive_failures,
                "avg_latency_ms": health.avg_latency_ms,
                "last_error": health.last_error,
            }
            for provider, health in self._health_status.items()
        }


# 全局路由器实例
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """获取全局模型路由器实例"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


async def init_model_router(
    openai_api_key: Optional[str] = None,
) -> ModelRouter:
    """
    初始化全局模型路由器

    Args:
        openai_api_key: OpenAI API密钥

    Returns:
        ModelRouter实例
    """
    router = get_model_router()
    await router.initialize(
        openai_api_key=openai_api_key,
    )
    return router
