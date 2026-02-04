"""
对话记忆管理服务
基于 LangChain 的记忆系统
"""
from typing import Any

from langchain.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
)
from langchain.schema import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Message
from services.llm_service import LLMService


class MemoryService:
    """对话记忆管理服务"""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        conversation_id: str,
        memory_type: str = "buffer_window",
    ):
        """
        初始化记忆服务
        
        Args:
            db: 数据库会话
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            memory_type: 记忆类型 (buffer/buffer_window/summary)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.memory_type = memory_type

        # 初始化 LLM（用于摘要）
        llm_service = LLMService(tenant_id)
        self.llm = llm_service.llm

        # 初始化记忆
        self.memory = self._initialize_memory()

    def _initialize_memory(
        self,
    ) -> ConversationBufferMemory | ConversationBufferWindowMemory | ConversationSummaryMemory:
        """
        初始化记忆实例
        
        Returns:
            LangChain Memory 实例
        """
        if self.memory_type == "buffer":
            # 完整的对话历史
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history",
            )
        elif self.memory_type == "buffer_window":
            # 滑动窗口记忆（最近 N 轮对话）
            return ConversationBufferWindowMemory(
                k=10,  # 保留最近 10 轮对话
                return_messages=True,
                memory_key="chat_history",
            )
        elif self.memory_type == "summary":
            # 摘要记忆（自动总结历史对话）
            return ConversationSummaryMemory(
                llm=self.llm,
                return_messages=True,
                memory_key="chat_history",
            )
        else:
            # 默认使用滑动窗口
            return ConversationBufferWindowMemory(
                k=10,
                return_messages=True,
                memory_key="chat_history",
            )

    async def load_history_from_db(self, limit: int = 20) -> None:
        """
        从数据库加载对话历史到记忆中
        
        Args:
            limit: 加载的最大消息数量
        """
        # 查询历史消息
        stmt = (
            select(Message)
            .where(
                Message.tenant_id == self.tenant_id,
                Message.conversation_id == self.conversation_id,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # 反转顺序（从旧到新）
        messages = list(reversed(messages))

        # 加载到记忆中
        for msg in messages:
            if msg.role == "user":
                self.memory.chat_memory.add_message(
                    HumanMessage(content=msg.content)
                )
            elif msg.role == "assistant":
                self.memory.chat_memory.add_message(AIMessage(content=msg.content))

    def add_user_message(self, content: str) -> None:
        """
        添加用户消息到记忆
        
        Args:
            content: 消息内容
        """
        self.memory.chat_memory.add_user_message(content)

    def add_ai_message(self, content: str) -> None:
        """
        添加 AI 消息到记忆
        
        Args:
            content: 消息内容
        """
        self.memory.chat_memory.add_ai_message(content)

    def get_memory_variables(self) -> dict[str, Any]:
        """
        获取记忆变量（用于 Prompt）
        
        Returns:
            记忆变量字典
        """
        return self.memory.load_memory_variables({})

    def get_chat_history(self) -> list[dict[str, str]]:
        """
        获取对话历史（格式化为字典列表）
        
        Returns:
            对话历史列表
        """
        memory_vars = self.get_memory_variables()
        chat_history = memory_vars.get("chat_history", [])

        formatted_history = []
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                formatted_history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_history.append({"role": "assistant", "content": msg.content})

        return formatted_history

    def clear_memory(self) -> None:
        """清空记忆"""
        self.memory.clear()

    def get_memory_stats(self) -> dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        chat_history = self.get_chat_history()

        return {
            "memory_type": self.memory_type,
            "message_count": len(chat_history),
            "conversation_id": self.conversation_id,
        }


class MemoryManager:
    """记忆管理器 - 管理多个会话的记忆"""

    def __init__(self):
        """初始化记忆管理器"""
        self._memories: dict[str, MemoryService] = {}

    def get_or_create_memory(
        self,
        db: AsyncSession,
        tenant_id: str,
        conversation_id: str,
        memory_type: str = "buffer_window",
    ) -> MemoryService:
        """
        获取或创建记忆服务
        
        Args:
            db: 数据库会话
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            memory_type: 记忆类型
            
        Returns:
            MemoryService 实例
        """
        key = f"{tenant_id}:{conversation_id}"

        if key not in self._memories:
            self._memories[key] = MemoryService(
                db=db,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                memory_type=memory_type,
            )

        return self._memories[key]

    def remove_memory(self, tenant_id: str, conversation_id: str) -> None:
        """
        移除记忆（会话结束时调用）
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
        """
        key = f"{tenant_id}:{conversation_id}"
        if key in self._memories:
            del self._memories[key]

    def clear_all(self) -> None:
        """清空所有记忆"""
        self._memories.clear()

    def get_stats(self) -> dict[str, Any]:
        """
        获取记忆管理器统计信息
        
        Returns:
            统计信息
        """
        return {
            "active_conversations": len(self._memories),
            "total_messages": sum(
                len(mem.get_chat_history()) for mem in self._memories.values()
            ),
        }


# 全局记忆管理器实例
memory_manager = MemoryManager()
