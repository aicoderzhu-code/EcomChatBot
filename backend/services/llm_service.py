"""
LLM 服务 - 封装 LangChain LLM 调用
支持多种 LLM 提供商（OpenAI、Anthropic、DeepSeek 等）
"""
from typing import Any
import logging

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
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
        if self._provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self.model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    anthropic_api_key=self._api_key,
                )
            except ImportError:
                logger.warning("langchain_anthropic not installed, falling back to ChatOpenAI")

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
        if self._provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self.model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    anthropic_api_key=self._api_key,
                    streaming=True,
                )
            except ImportError:
                pass

        return ChatOpenAI(
            model=self.model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            openai_api_key=self._api_key,
            openai_api_base=self._api_base,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

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
        # 构建消息列表
        langchain_messages = []

        # 添加系统提示词
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        # 转换消息格式
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))

        # 调用 LLM
        response = await self.llm.ainvoke(langchain_messages)

        # 获取原始回复
        content = response.content

        # 应用安全过滤（脱敏PII数据）
        if enable_safety_filter:
            filtered_content = filter_llm_output(content)

            # 如果内容被修改，记录日志
            if filtered_content != content:
                logger.info(
                    f"LLM output filtered for tenant {self.tenant_id}: "
                    f"Original length: {len(content)}, Filtered length: {len(filtered_content)}"
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
