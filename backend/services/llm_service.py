"""
LLM 服务 - 封装 LangChain LLM 调用
支持多种 LLM 提供商（OpenAI 兼容接口）
"""
from typing import Any, AsyncIterator
import logging

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from api.content_filter import filter_llm_output
from core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 服务类"""

    def __init__(self, tenant_id: str, model_name: str | None = None, model_config=None):
        """
        初始化 LLM 服务

        Args:
            tenant_id: 租户 ID
            model_name: 模型名称，如果为 None 则使用默认模型（当 model_config 存在时忽略）
            model_config: ModelConfig 实例，优先于环境变量配置
        """
        self.tenant_id = tenant_id
        self._model_config = model_config

        if model_config is not None:
            self.model_name = model_config.model_name
            self._provider = model_config.provider
            self._api_key = model_config.api_key or settings.openai_api_key
            self._api_base = model_config.api_base or settings.openai_api_base
            self._temperature = float(model_config.temperature) if model_config.temperature is not None else 0.7
            self._max_tokens = model_config.max_tokens or 1000
        else:
            self.model_name = model_name or settings.default_llm_model
            self._provider = "openai"
            self._api_key = settings.openai_api_key
            self._api_base = settings.openai_api_base
            self._temperature = 0.7
            self._max_tokens = 1000

        # 初始化 LLM
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """
        初始化 LLM 实例，根据 provider 选择合适的实现
        """
        return ChatOpenAI(
            model=self.model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            openai_api_key=self._api_key,
            openai_api_base=self._api_base,
            streaming=False,
        )

    def get_streaming_llm(self):
        """获取支持流式输出的 LLM 实例"""
        return ChatOpenAI(
            model=self.model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            openai_api_key=self._api_key,
            openai_api_base=self._api_base,
            streaming=True,
        )

    def _build_lc_messages(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> list:
        """Convert dict messages to LangChain message objects."""
        lc_messages = []
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
        return lc_messages

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        enable_safety_filter: bool = True,
    ) -> AsyncIterator[dict]:
        """
        Real streaming generation via LangChain's astream().

        Yields:
            {"type": "chunk", "content": "token text"}
            {"type": "done", "content": "full text", "input_tokens": N,
             "output_tokens": N, "model": "..."}
        """
        streaming_llm = self.get_streaming_llm()
        lc_messages = self._build_lc_messages(messages, system_prompt)

        full_content = ""
        async for chunk in streaming_llm.astream(lc_messages):
            token = chunk.content or ""
            if token:
                full_content += token
                yield {"type": "chunk", "content": token}

        if enable_safety_filter:
            filtered = filter_llm_output(full_content)
            if filtered != full_content:
                logger.info(
                    "LLM stream output filtered for tenant %s: %d -> %d chars",
                    self.tenant_id, len(full_content), len(filtered),
                )
                full_content = filtered

        yield {
            "type": "done",
            "content": full_content,
            "input_tokens": self.count_tokens(
                " ".join(m.get("content", "") for m in messages)
            ),
            "output_tokens": self.count_tokens(full_content),
            "model": self.model_name,
            "provider": self._provider,
        }

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        enable_safety_filter: bool = True,
    ) -> str:
        """
        生成回复

        Args:
            messages: 对话历史 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示词
            enable_safety_filter: 是否启用安全过滤（默认True）

        Returns:
            AI 回复内容（已过滤PII等敏感信息）
        """
        langchain_messages = self._build_lc_messages(messages, system_prompt)

        response = await self.llm.ainvoke(langchain_messages)
        content = response.content

        if enable_safety_filter:
            filtered_content = filter_llm_output(content)
            if filtered_content != content:
                logger.info(
                    "LLM output filtered for tenant %s: %d -> %d chars",
                    self.tenant_id, len(content), len(filtered_content),
                )
            return filtered_content

        return content

    async def generate_with_functions(
        self,
        messages: list[dict[str, str]],
        functions: list[dict[str, Any]],
        system_prompt: str | None = None,
        enable_safety_filter: bool = True,
    ) -> dict[str, Any]:
        """
        使用函数调用生成回复

        Args:
            messages: 对话历史
            functions: 函数定义列表
            system_prompt: 系统提示词
            enable_safety_filter: 是否启用安全过滤（默认True）

        Returns:
            包含回复和函数调用信息的字典
        """
        # 构建消息
        langchain_messages = []
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

        # 绑定函数
        llm_with_functions = self.llm.bind_functions(functions)

        # 调用
        response = await llm_with_functions.ainvoke(langchain_messages)

        # 解析响应
        content = response.content

        # 应用安全过滤
        if enable_safety_filter and content:
            content = filter_llm_output(content)

        result = {
            "content": content,
            "function_call": None,
        }

        # 检查是否有函数调用
        if hasattr(response, "additional_kwargs"):
            function_call = response.additional_kwargs.get("function_call")
            if function_call:
                result["function_call"] = {
                    "name": function_call.get("name"),
                    "arguments": function_call.get("arguments"),
                }

        return result

    def count_tokens(self, text: str) -> int:
        """
        统计 Token 数量
        
        Args:
            text: 文本内容
            
        Returns:
            Token 数量
        """
        # 使用 LangChain 的 token 计数
        return self.llm.get_num_tokens(text)

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            "model_name": self.model_name,
            "tenant_id": self.tenant_id,
            "provider": self._provider,
            "supports_streaming": True,
            "supports_functions": self._provider != "anthropic",
        }
