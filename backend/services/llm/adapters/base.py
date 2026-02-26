"""
LLM适配器基类

定义所有LLM适配器的通用接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Dict, Any
from enum import Enum


class LLMProvider(str, Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ZHIPU = "zhipu"          # 智谱AI
    QWEN = "qwen"            # 通义千问
    SILICONFLOW = "siliconflow"  # 硅基流动
    META = "meta"            # Meta (自定义 base URL)
    PRIVATE = "private"      # 私有/自托管部署


@dataclass
class LLMConfig:
    """LLM调用配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    timeout: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
        }


@dataclass
class LLMUsage:
    """Token使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: str
    usage: LLMUsage
    finish_reason: str = "stop"
    raw_response: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "total_tokens": self.usage.total_tokens,
            },
            "finish_reason": self.finish_reason,
        }


@dataclass
class StreamChunk:
    """流式响应块"""
    content: str
    is_final: bool = False
    usage: Optional[LLMUsage] = None
    finish_reason: Optional[str] = None


class LLMAdapter(ABC):
    """
    LLM适配器基类

    所有LLM提供商的适配器都需要继承此类并实现抽象方法
    """

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """提供商标识"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """
        生成回复

        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            config: 生成配置

        Returns:
            LLMResponse
        """
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncIterator[StreamChunk]:
        """
        流式生成回复

        Args:
            messages: 消息列表
            config: 生成配置

        Yields:
            StreamChunk
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str, model: str = None) -> int:
        """
        计算文本Token数

        Args:
            text: 要计算的文本
            model: 模型名称（不同模型tokenizer可能不同）

        Returns:
            Token数量
        """
        pass

    def count_messages_tokens(
        self,
        messages: List[Dict[str, str]],
        model: str = None
    ) -> int:
        """
        计算消息列表的Token数

        Args:
            messages: 消息列表
            model: 模型名称

        Returns:
            总Token数
        """
        total = 0
        for msg in messages:
            # 每条消息约有4个token的格式开销
            total += self.count_tokens(msg.get("content", ""), model) + 4
        # 对话格式开销约3个token
        total += 3
        return total

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            response = await self.generate(
                messages=[{"role": "user", "content": "hi"}],
                config=LLMConfig(
                    model=self.supported_models[0],
                    max_tokens=5,
                    temperature=0
                )
            )
            return bool(response.content)
        except Exception:
            return False

    def supports_model(self, model: str) -> bool:
        """
        检查是否支持指定模型

        Args:
            model: 模型名称

        Returns:
            是否支持
        """
        return model in self.supported_models

    def get_default_model(self) -> str:
        """
        获取默认模型

        Returns:
            默认模型名称
        """
        return self.supported_models[0] if self.supported_models else ""


class LLMError(Exception):
    """LLM调用错误"""

    def __init__(
        self,
        message: str,
        provider: str = None,
        model: str = None,
        status_code: int = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable


class RateLimitError(LLMError):
    """速率限制错误"""

    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, retryable=True, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """认证错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class ModelNotFoundError(LLMError):
    """模型不存在错误"""

    def __init__(self, model: str, provider: str, **kwargs):
        super().__init__(
            f"Model '{model}' not found for provider '{provider}'",
            provider=provider,
            model=model,
            retryable=False,
            **kwargs
        )


class ContextLengthExceededError(LLMError):
    """上下文长度超限错误"""

    def __init__(self, message: str, max_tokens: int = None, **kwargs):
        super().__init__(message, retryable=False, **kwargs)
        self.max_tokens = max_tokens
