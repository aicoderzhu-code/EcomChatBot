"""
对话摘要自动生成服务
"""
import logging
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationSummaryService:
    """对话摘要服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def _get_messages(self, conversation_id: str) -> list[Message]:
        """获取对话的所有消息"""
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.tenant_id == self.tenant_id,
                    Message.conversation_id == conversation_id,
                )
            )
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _format_messages_for_summary(self, messages: list[Message]) -> str:
        """将消息格式化为摘要输入"""
        formatted = []
        for msg in messages:
            if msg.role == "user":
                formatted.append(f"用户：{msg.content}")
            elif msg.role == "assistant":
                formatted.append(f"客服：{msg.content}")
        return "\n".join(formatted)

    def _get_summary_prompt(self, conversation_text: str) -> str:
        """获取摘要生成的 prompt"""
        return f"""请对以下客服对话生成一段简洁的摘要。

## 要求
1. 概述用户的主要问题或需求
2. 说明客服提供的解决方案或回答
3. 记录最终结论或处理结果
4. 如果有未解决的问题也要提及
5. 摘要控制在 100-200 字以内

## 对话内容
{conversation_text}

## 摘要："""

    async def generate_summary(
        self,
        conversation_id: str,
    ) -> str:
        """
        生成对话摘要

        Args:
            conversation_id: 会话ID

        Returns:
            生成的摘要文本
        """
        from services.llm_service import LLMService

        messages = await self._get_messages(conversation_id)
        if len(messages) < 3:
            return self._generate_simple_summary(messages)

        conversation_text = self._format_messages_for_summary(messages)
        prompt = self._get_summary_prompt(conversation_text)

        try:
            llm_service = LLMService()
            result = await llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的对话摘要生成助手，擅长提取对话中的关键信息。",
            )
            summary = result.get("response", "") if isinstance(result, dict) else str(result)

            # 保存摘要到数据库
            await self._save_summary(conversation_id, summary)

            return summary
        except Exception as e:
            logger.error("Failed to generate summary for %s: %s", conversation_id, e)
            simple_summary = self._generate_simple_summary(messages)
            await self._save_summary(conversation_id, simple_summary)
            return simple_summary

    async def generate_incremental_summary(
        self,
        conversation_id: str,
        old_summary: str,
        new_messages: list[Message],
    ) -> str:
        """
        增量更新摘要（适用于长对话）
        """
        from services.llm_service import LLMService

        new_text = self._format_messages_for_summary(new_messages)
        prompt = f"""请基于已有摘要和新增的对话内容，更新摘要。

## 已有摘要
{old_summary}

## 新增对话
{new_text}

## 要求
1. 合并旧摘要和新对话的信息
2. 保持摘要简洁，控制在 100-200 字
3. 突出最新的进展和结论

## 更新后的摘要："""

        try:
            llm_service = LLMService()
            result = await llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的对话摘要生成助手。",
            )
            summary = result.get("response", "") if isinstance(result, dict) else str(result)
            await self._save_summary(conversation_id, summary)
            return summary
        except Exception as e:
            logger.error("Failed to generate incremental summary: %s", e)
            return old_summary

    def _generate_simple_summary(self, messages: list[Message]) -> str:
        """生成简单摘要（不使用LLM）"""
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return "无用户消息"

        first_question = user_messages[0].content[:100]
        return f"用户咨询：{first_question}{'...' if len(user_messages[0].content) > 100 else ''}"

    async def _save_summary(self, conversation_id: str, summary: str):
        """保存摘要到数据库"""
        stmt = select(Conversation).where(
            and_(
                Conversation.tenant_id == self.tenant_id,
                Conversation.conversation_id == conversation_id,
            )
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.summary = summary
            conversation.summary_updated_at = datetime.utcnow()
            await self.db.commit()
