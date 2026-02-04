"""
LLM 服务 - 封装 LangChain LLM 调用
支持多种 LLM 提供商（OpenAI、Azure OpenAI 等）
"""
from typing import Any

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.config import settings


class LLMService:
    """LLM 服务类"""

    def __init__(self, tenant_id: str, model_name: str | None = None):
        """
        初始化 LLM 服务
        
        Args:
            tenant_id: 租户 ID
            model_name: 模型名称，如果为 None 则使用默认模型
        """
        self.tenant_id = tenant_id
        self.model_name = model_name or settings.default_llm_model

        # 初始化 LLM
        self.llm = self._initialize_llm()

    def _initialize_llm(self) -> ChatOpenAI:
        """
        初始化 LLM 实例
        
        Returns:
            ChatOpenAI 实例
        """
        # TODO: 根据租户配置选择不同的 LLM 提供商
        # 目前默认使用 OpenAI
        return ChatOpenAI(
            model=self.model_name,
            temperature=0.7,
            max_tokens=1000,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=False,  # 默认不流式
        )

    def get_streaming_llm(self) -> ChatOpenAI:
        """获取支持流式输出的 LLM 实例"""
        return ChatOpenAI(
            model=self.model_name,
            temperature=0.7,
            max_tokens=1000,
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """
        生成回复
        
        Args:
            messages: 对话历史 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示词
            
        Returns:
            AI 回复内容
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

        return response.content

    async def generate_with_functions(
        self,
        messages: list[dict[str, str]],
        functions: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        使用函数调用生成回复
        
        Args:
            messages: 对话历史
            functions: 函数定义列表
            system_prompt: 系统提示词
            
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
        result = {
            "content": response.content,
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
            "provider": "openai",  # TODO: 根据实际配置返回
            "supports_streaming": True,
            "supports_functions": True,
        }
