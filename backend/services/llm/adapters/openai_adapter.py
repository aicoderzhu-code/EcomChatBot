"""
OpenAI LLM适配器

支持OpenAI API及兼容接口
"""
import logging
from typing import List, Dict, AsyncIterator, Optional

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
    ContextLengthExceededError,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMAdapter):
    """
    OpenAI适配器

    支持GPT-4, GPT-3.5等模型
    也可用于OpenAI兼容的API（如Azure OpenAI）
    """

    # 模型及其上下文窗口大小
    MODEL_CONTEXT_WINDOWS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        default_model: str = "gpt-4o-mini"
    ):
        """
        初始化OpenAI适配器

        Args:
            api_key: OpenAI API密钥
            base_url: 自定义API基础URL（可选，用于Azure等）
            organization: 组织ID（可选）
            default_model: 默认模型
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("请安装openai包: pip install openai")

        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model

        # 创建异步客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
        )

        # Token计数器
        self._tokenizer = None

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    @property
    def supported_models(self) -> List[str]:
        return list(self.MODEL_CONTEXT_WINDOWS.keys())

    def get_context_window(self, model: str) -> int:
        """获取模型的上下文窗口大小"""
        return self.MODEL_CONTEXT_WINDOWS.get(model, 8192)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """生成回复"""
        try:
            response = await self.client.chat.completions.create(
                model=config.model or self._default_model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider.value,
                usage=LLMUsage(
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                ),
                finish_reason=choice.finish_reason or "stop",
                raw_response=response,
            )

        except Exception as e:
            self._handle_error(e, config.model)

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncIterator[StreamChunk]:
        """流式生成回复"""
        try:
            stream = await self.client.chat.completions.create(
                model=config.model or self._default_model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                if not chunk.choices:
                    # 最后一个chunk包含usage信息
                    if chunk.usage:
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            usage=LLMUsage(
                                input_tokens=chunk.usage.prompt_tokens,
                                output_tokens=chunk.usage.completion_tokens,
                            ),
                        )
                    continue

                choice = chunk.choices[0]
                content = choice.delta.content or ""
                finish_reason = choice.finish_reason

                yield StreamChunk(
                    content=content,
                    is_final=finish_reason is not None,
                    finish_reason=finish_reason,
                )

        except Exception as e:
            self._handle_error(e, config.model)

    def count_tokens(self, text: str, model: str = None) -> int:
        """计算Token数"""
        if self._tokenizer is None:
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                # 如果没有tiktoken，使用估算
                return len(text) // 4

        return len(self._tokenizer.encode(text))

    def _handle_error(self, error: Exception, model: str = None):
        """处理API错误"""
        error_str = str(error)

        # 速率限制
        if "rate_limit" in error_str.lower() or "429" in error_str:
            raise RateLimitError(
                message=error_str,
                provider=self.provider.value,
                model=model,
            )

        # 认证错误
        if "authentication" in error_str.lower() or "401" in error_str:
            raise AuthenticationError(
                message=error_str,
                provider=self.provider.value,
                model=model,
            )

        # 上下文超限
        if "context_length" in error_str.lower() or "maximum context" in error_str.lower():
            raise ContextLengthExceededError(
                message=error_str,
                provider=self.provider.value,
                model=model,
            )

        # 通用错误
        raise LLMError(
            message=error_str,
            provider=self.provider.value,
            model=model,
            retryable="timeout" in error_str.lower() or "connection" in error_str.lower(),
        )
