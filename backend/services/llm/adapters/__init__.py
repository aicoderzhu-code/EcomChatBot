"""
LLM适配器模块

提供多LLM提供商的统一适配接口
"""
from .base import (
    LLMAdapter,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMProvider,
    StreamChunk,
    LLMError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError,
    ContextLengthExceededError,
)
from .openai_adapter import OpenAIAdapter
from .deepseek_adapter import DeepSeekAdapter
from .anthropic_adapter import AnthropicAdapter

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
    "DeepSeekAdapter",
    "AnthropicAdapter",
]
