"""
Anthropic Claude LLM适配器

支持Claude 3系列模型
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


class AnthropicAdapter(LLMAdapter):
    """
    Anthropic Claude适配器

    支持Claude 3 Opus、Sonnet、Haiku等模型
    API文档: https://docs.anthropic.com/claude/reference/
    """

    # 模型及其上下文窗口大小
    MODEL_CONTEXT_WINDOWS = {
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-5-haiku-20241022": 200000,
        # 简化别名
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "claude-3.5-sonnet": 200000,
        "claude-3.5-haiku": 200000,
    }

    # 别名映射到完整模型名
    MODEL_ALIASES = {
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
        "claude-3-haiku": "claude-3-haiku-20240307",
        "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3.5-haiku": "claude-3-5-haiku-20241022",
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: str = "claude-3-5-sonnet-20241022"
    ):
        """
        初始化Anthropic适配器

        Args:
            api_key: Anthropic API密钥
            base_url: 自定义API基础URL（可选）
            default_model: 默认模型
        """
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._client = None

    def _get_client(self):
        """懒加载客户端"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError("请安装anthropic包: pip install anthropic")

            kwargs = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url

            self._client = AsyncAnthropic(**kwargs)
        return self._client

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    @property
    def supported_models(self) -> List[str]:
        return list(self.MODEL_CONTEXT_WINDOWS.keys())

    def get_context_window(self, model: str) -> int:
        """获取模型的上下文窗口大小"""
        return self.MODEL_CONTEXT_WINDOWS.get(model, 200000)

    def _resolve_model(self, model: str) -> str:
        """解析模型别名"""
        return self.MODEL_ALIASES.get(model, model)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """
        转换消息格式为Anthropic格式

        Anthropic要求system消息单独传递

        Returns:
            (system_prompt, messages)
        """
        system_prompt = None
        converted_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
            else:
                # Anthropic只支持user和assistant角色
                anthropic_role = "assistant" if role == "assistant" else "user"
                converted_messages.append({
                    "role": anthropic_role,
                    "content": content,
                })

        return system_prompt, converted_messages

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """生成回复"""
        try:
            client = self._get_client()
            model = self._resolve_model(config.model or self._default_model)
            system_prompt, converted_messages = self._convert_messages(messages)

            kwargs = {
                "model": model,
                "messages": converted_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if config.stop:
                kwargs["stop_sequences"] = config.stop

            response = await client.messages.create(**kwargs)

            # 提取内容
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider.value,
                usage=LLMUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                ),
                finish_reason=response.stop_reason or "end_turn",
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
            client = self._get_client()
            model = self._resolve_model(config.model or self._default_model)
            system_prompt, converted_messages = self._convert_messages(messages)

            kwargs = {
                "model": model,
                "messages": converted_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if config.stop:
                kwargs["stop_sequences"] = config.stop

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(
                        content=text,
                        is_final=False,
                    )

                # 获取最终的消息以获取usage信息
                final_message = await stream.get_final_message()
                yield StreamChunk(
                    content="",
                    is_final=True,
                    usage=LLMUsage(
                        input_tokens=final_message.usage.input_tokens,
                        output_tokens=final_message.usage.output_tokens,
                    ),
                    finish_reason=final_message.stop_reason or "end_turn",
                )

        except Exception as e:
            self._handle_error(e, config.model)

    def count_tokens(self, text: str, model: str = None) -> int:
        """
        计算Token数

        Claude使用自己的tokenizer，这里使用估算
        """
        # Claude大约每4个字符一个token（英文）
        # 中文大约1.5个字符一个token
        # 这里使用保守估算
        return len(text) // 3

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
        if "authentication" in error_str.lower() or "401" in error_str or "invalid_api_key" in error_str.lower():
            raise AuthenticationError(
                message=error_str,
                provider=self.provider.value,
                model=model,
            )

        # 上下文超限
        if "context_length" in error_str.lower() or "too long" in error_str.lower():
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
