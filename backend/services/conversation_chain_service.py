"""
对话链服务 - 整合 LLM、Memory 和 Prompt
基于 LangChain 构建完整的对话流程
"""
from typing import Any

from langchain.chains import ConversationChain, LLMChain
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_service import LLMService
from services.memory_service import MemoryService, memory_manager
from services.prompt_service import PromptService


class ConversationChainService:
    """对话链服务"""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        conversation_id: str,
        platform_name: str = "电商平台",
    ):
        """
        初始化对话链服务
        
        Args:
            db: 数据库会话
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            platform_name: 平台名称
        """
        self.db = db
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.platform_name = platform_name

        # 初始化服务
        self.llm_service = LLMService(tenant_id)
        self.prompt_service = PromptService()

        # 获取或创建记忆
        self.memory = memory_manager.get_or_create_memory(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            memory_type="buffer_window",
        )

    async def initialize(self) -> None:
        """初始化：加载历史对话，并从 DB 加载默认 LLM 配置"""
        await self.memory.load_history_from_db(limit=20)

        # 从数据库加载默认 LLM 配置（优先于环境变量）
        try:
            from services.model_config_service import ModelConfigService
            model_config = await ModelConfigService(self.db, self.tenant_id).get_default_model(use_case="dialogue")
            if model_config:
                self.llm_service = LLMService(self.tenant_id, model_config=model_config)
        except Exception:
            pass  # 加载失败时保持使用环境变量配置

    async def chat(
        self,
        user_input: str,
        user_info: dict[str, Any] | None = None,
        tenant_custom_instructions: str | None = None,
    ) -> dict[str, Any]:
        """
        处理用户输入，生成回复
        
        Args:
            user_input: 用户输入
            user_info: 用户信息
            tenant_custom_instructions: 租户自定义指令
            
        Returns:
            包含回复和元数据的字典
        """
        # 1. 获取系统提示词
        system_prompt = self.prompt_service.get_system_prompt(
            platform_name=self.platform_name,
            user_info=user_info,
            tenant_custom_instructions=tenant_custom_instructions,
        )

        # 2. 获取对话历史
        chat_history = self.memory.get_chat_history()

        # 3. 构建消息列表
        messages = chat_history.copy()
        messages.append({"role": "user", "content": user_input})

        # 4. 调用 LLM 生成回复
        response = await self.llm_service.generate_response(
            messages=messages,
            system_prompt=system_prompt,
        )

        # 5. 更新记忆
        self.memory.add_user_message(user_input)
        self.memory.add_ai_message(response)

        # 6. 计算 Token
        input_tokens = self.llm_service.count_tokens(user_input)
        output_tokens = self.llm_service.count_tokens(response)

        return {
            "response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": self.llm_service.model_name,
        }

    async def chat_with_rag(
        self,
        user_input: str,
        knowledge_items: list[dict[str, Any]],
        user_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        使用 RAG（检索增强生成）处理用户输入
        
        Args:
            user_input: 用户输入
            knowledge_items: 检索到的知识库项
            user_info: 用户信息
            
        Returns:
            包含回复和元数据的字典
        """
        # 1. 构建知识库上下文
        context = self.prompt_service.build_context_from_knowledge(knowledge_items)

        # 2. 获取 RAG Prompt 模板
        prompt_template = self.prompt_service.get_rag_prompt_template()

        # 3. 获取对话历史
        chat_history = self.memory.get_chat_history()

        # 转换为 LangChain 消息格式
        from langchain.schema import AIMessage, HumanMessage

        lc_messages = []
        for msg in chat_history:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        # 4. 格式化 Prompt
        formatted_prompt = prompt_template.format_messages(
            context=context,
            question=user_input,
            chat_history=lc_messages,
        )

        # 5. 调用 LLM
        response = await self.llm_service.llm.ainvoke(formatted_prompt)
        response_text = response.content

        # 6. 更新记忆
        self.memory.add_user_message(user_input)
        self.memory.add_ai_message(response_text)

        # 7. 计算 Token
        input_tokens = self.llm_service.count_tokens(
            context + user_input
        )  # 包含上下文
        output_tokens = self.llm_service.count_tokens(response_text)

        return {
            "response": response_text,
            "context_used": len(knowledge_items),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "model": self.llm_service.model_name,
            "sources": [
                {"title": item.get("title"), "source": item.get("source")}
                for item in knowledge_items
            ],
        }

    async def classify_intent(self, user_input: str) -> str:
        """
        分类用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            意图类别
        """
        prompt = self.prompt_service.get_intent_classification_prompt()
        formatted_prompt = prompt.format(question=user_input)

        messages = [{"role": "user", "content": formatted_prompt}]

        response = await self.llm_service.generate_response(messages=messages)

        # 提取意图（去除空格和换行）
        intent = response.strip().upper()

        return intent

    async def extract_entities(self, user_input: str) -> dict[str, Any]:
        """
        提取实体
        
        Args:
            user_input: 用户输入
            
        Returns:
            提取的实体字典
        """
        prompt = self.prompt_service.get_entity_extraction_prompt()
        formatted_prompt = prompt.format(question=user_input)

        messages = [{"role": "user", "content": formatted_prompt}]

        response = await self.llm_service.generate_response(messages=messages)

        # 尝试解析 JSON
        import json

        try:
            entities = json.loads(response)
        except json.JSONDecodeError:
            entities = {}

        return entities

    def get_conversation_summary(self) -> str:
        """
        获取对话摘要
        
        Returns:
            对话摘要文本
        """
        chat_history = self.memory.get_chat_history()

        if not chat_history:
            return "暂无对话内容"

        # 简单摘要：前3轮对话
        summary_parts = []
        for idx, msg in enumerate(chat_history[:6], 1):  # 3轮 * 2条消息
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:50]  # 截取前50个字符
            summary_parts.append(f"{role}: {content}...")

        return "\n".join(summary_parts)

    def clear_context(self) -> None:
        """清空对话上下文"""
        self.memory.clear_memory()

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        memory_stats = self.memory.get_memory_stats()

        return {
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "model": self.llm_service.model_name,
            "memory_type": memory_stats["memory_type"],
            "message_count": memory_stats["message_count"],
        }


# 简化的对话助手
async def simple_chat(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
    user_input: str,
    use_rag: bool = False,
    knowledge_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    简化的对话接口
    
    Args:
        db: 数据库会话
        tenant_id: 租户 ID
        conversation_id: 会话 ID
        user_input: 用户输入
        use_rag: 是否使用 RAG
        knowledge_items: 知识库项（当 use_rag=True 时需要）
        
    Returns:
        对话结果
    """
    # 创建对话链
    chain = ConversationChainService(
        db=db,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )

    # 初始化（加载历史）
    await chain.initialize()

    # 生成回复
    if use_rag and knowledge_items:
        result = await chain.chat_with_rag(
            user_input=user_input,
            knowledge_items=knowledge_items,
        )
    else:
        result = await chain.chat(user_input=user_input)

    return result
