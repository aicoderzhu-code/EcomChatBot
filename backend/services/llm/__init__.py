"""
LLM服务模块

提供多LLM提供商支持、智能路由和统一接口
"""
from .adapters import (
    # 基类和数据类型
    LLMAdapter,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMProvider,
    StreamChunk,
    # 错误类型
    LLMError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError,
    ContextLengthExceededError,
    # 适配器实现
    OpenAIAdapter,
)
from .router import (
    ModelRouter,
    RoutingStrategy,
    IntentCategory,
    ProviderHealth,
    ProviderConfig,
    TenantPreferences,
    get_model_router,
    init_model_router,
)

__all__ = [
    # 基类和数据类型
    "LLMAdapter",
    "LLMConfig",
    "LLMResponse",
    "LLMUsage",
    "LLMProvider",
    "StreamChunk",
    # 错误类型
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "ModelNotFoundError",
    "ContextLengthExceededError",
    # 适配器实现
    "OpenAIAdapter",
    # 路由器
    "ModelRouter",
    "RoutingStrategy",
    "IntentCategory",
    "ProviderHealth",
    "ProviderConfig",
    "TenantPreferences",
    "get_model_router",
    "init_model_router",
]
