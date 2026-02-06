"""
Token计数和上下文管理服务
"""
import tiktoken
from typing import list, tuple
from sqlalchemy.ext.asyncio import AsyncSession

from models import Message
from services.llm_service import LLMService


class TokenService:
    """Token计数和上下文管理服务"""

    # 默认Token限制
    MAX_CONTEXT_TOKENS = 4000  # 最大上下文Token数
    WARNING_THRESHOLD = 3000   # 警告阈值
    SUMMARY_THRESHOLD = 3500   # 摘要压缩阈值

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        # 初始化tokenizer（使用cl100k_base编码，适用于GPT-4）
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # 回退到简单计数（1 token ≈ 0.75 words）
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量

        Args:
            text: 输入文本

        Returns:
            Token数量
        """
        if not text:
            return 0

        if self.encoding:
            try:
                tokens = self.encoding.encode(text)
                return len(tokens)
            except Exception:
                pass

        # 回退计算：1 token ≈ 4 characters (英文) 或 1.5 characters (中文)
        # 简化计算：假设平均每个token 3个字符
        return len(text) // 3

    async def count_conversation_tokens(
        self, conversation_id: str, include_system_prompt: bool = True
    ) -> int:
        """
        计算对话的上下文Token总数

        Args:
            conversation_id: 对话ID
            include_system_prompt: 是否包含系统提示词

        Returns:
            Token总数
        """
        from sqlalchemy import select
        from services.conversation_service import ConversationService

        conv_service = ConversationService(self.db, self.tenant_id)

        # 获取对话历史
        messages = await conv_service.get_messages(
            conversation_id, limit=100  # 获取最近100条消息
        )

        total_tokens = 0

        # 系统提示词Token
        if include_system_prompt:
            system_prompt = await self._get_system_prompt()
            total_tokens += self.count_tokens(system_prompt)

        # 消息Token
        for msg in messages:
            total_tokens += self.count_tokens(msg.content)

        return total_tokens

    async def check_context_limit(
        self, conversation_id: str, new_message: str | None = None
    ) -> tuple[bool, int, str]:
        """
        检查是否超过上下文窗口限制

        Args:
            conversation_id: 对话ID
            new_message: 新消息内容（可选）

        Returns:
            (是否超限, 当前Token数, 建议)
        """
        current_tokens = await self.count_conversation_tokens(conversation_id)

        if new_message:
            current_tokens += self.count_tokens(new_message)

        if current_tokens > self.MAX_CONTEXT_TOKENS:
            return (
                False,
                current_tokens,
                f"上下文超出限制（{current_tokens}/{self.MAX_CONTEXT_TOKENS} tokens），"
                "将对历史消息进行摘要压缩"
            )
        elif current_tokens > self.WARNING_THRESHOLD:
            return (
                True,
                current_tokens,
                f"上下文接近限制（{current_tokens}/{self.MAX_CONTEXT_TOKENS} tokens）"
            )
        else:
            return (True, current_tokens, "上下文正常")

    async def should_summarize(self, conversation_id: str) -> bool:
        """
        判断是否需要对对话进行摘要

        Args:
            conversation_id: 对话ID

        Returns:
            是否需要摘要
        """
        current_tokens = await self.count_conversation_tokens(conversation_id)
        return current_tokens > self.SUMMARY_THRESHOLD

    async def summarize_conversation(
        self, conversation_id: str
    ) -> str:
        """
        对对话历史进行摘要压缩

        Args:
            conversation_id: 对话ID

        Returns:
            摘要文本
        """
        from sqlalchemy import select
        from services.conversation_service import ConversationService

        conv_service = ConversationService(self.db, self.tenant_id)

        # 获取对话历史
        messages = await conv_service.get_messages(
            conversation_id, limit=50
        )

        if not messages:
            return ""

        # 构建摘要提示词
        summary_prompt = """请将以下对话历史压缩成简洁的摘要，保留关键信息：

摘要要求：
1. 用户的主要问题或需求
2. 提供的关键信息（如订单号、商品等）
3. 已讨论的要点
4. 当前状态或待解决问题

对话内容：
"""

        for msg in messages[:20]:  # 只摘要最近20条消息
            summary_prompt += f"\n{msg.role}: {msg.content}"

        summary_prompt += "\n\n请生成摘要："

        # 调用LLM生成摘要
        llm_service = LLMService(self.db, self.tenant_id)
        try:
            from langchain_core.messages import HumanMessage

            response = await llm_service.generate_response(
                messages=[HumanMessage(content=summary_prompt)],
                tenant_id=self.tenant_id
            )

            summary = response.get("content", "").strip()

            # 保存摘要到对话记录
            conversation = await conv_service.get_conversation(conversation_id)
            if conversation:
                conversation.summary = summary
                await self.db.commit()

            return summary

        except Exception as e:
            # 摘要失败，返回简单摘要
            return f"对话包含{len(messages)}条消息，涉及用户查询和系统回复。"

    async def get_messages_within_limit(
        self, conversation_id: str, max_tokens: int | None = None
    ) -> list[Message]:
        """
        获取Token限制内的消息列表

        Args:
            conversation_id: 对话ID
            max_tokens: 最大Token数，默认使用MAX_CONTEXT_TOKENS

        Returns:
            消息列表（从新到旧）
        """
        if max_tokens is None:
            max_tokens = self.MAX_CONTEXT_TOKENS

        from sqlalchemy import select
        from services.conversation_service import ConversationService

        conv_service = ConversationService(self.db, self.tenant_id)

        # 获取所有消息（从新到旧）
        all_messages = await conv_service.get_messages(
            conversation_id, limit=200
        )

        # 从最新消息开始，逐步添加直到接近Token限制
        selected_messages = []
        current_tokens = 0

        # 系统提示词Token
        system_prompt = await self._get_system_prompt()
        current_tokens += self.count_tokens(system_prompt)

        for msg in reversed(all_messages):  # 反转，从旧到新
            msg_tokens = self.count_tokens(msg.content)

            if current_tokens + msg_tokens > max_tokens:
                break

            selected_messages.append(msg)
            current_tokens += msg_tokens

        # 再次反转，恢复从新到旧的顺序
        selected_messages.reverse()

        return selected_messages

    async def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        from services.prompt_service import PromptService

        prompt_service = PromptService()
        return await prompt_service.get_system_prompt(self.tenant_id)
