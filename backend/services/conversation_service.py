"""
对话管理服务
"""
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConversationNotFoundException
from core.security import generate_conversation_id
from models import Conversation, Message, User
from services.usage_service import UsageService


class ConversationService:
    """对话管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.usage_service = UsageService(db)

    async def get_or_create_user(
        self,
        user_external_id: str,
        user_data: dict | None = None,
    ) -> User:
        """获取或创建用户"""
        stmt = select(User).where(
            and_(
                User.tenant_id == self.tenant_id,
                User.user_external_id == user_external_id,
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                tenant_id=self.tenant_id,
                user_external_id=user_external_id,
                nickname=user_data.get("nickname") if user_data else None,
                email=user_data.get("email") if user_data else None,
                phone=user_data.get("phone") if user_data else None,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def create_conversation(
        self,
        user_external_id: str,
        channel: str = "web",
        user_data: dict | None = None,
    ) -> Conversation:
        """
        创建会话
        """
        # 获取或创建用户
        user = await self.get_or_create_user(user_external_id, user_data)

        # 创建会话
        conversation_id = generate_conversation_id()
        conversation = Conversation(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            user_id=user.id,
            channel=channel,
            status="active",
            start_time=datetime.utcnow(),
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        # 记录用量
        await self.usage_service.record_conversation(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
        )

        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """获取会话"""
        from sqlalchemy.orm import selectinload
        
        stmt = select(Conversation).where(
            and_(
                Conversation.tenant_id == self.tenant_id,
                Conversation.conversation_id == conversation_id,
            )
        ).options(
            selectinload(Conversation.user)
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ConversationNotFoundException(conversation_id)

        return conversation

    async def list_conversations(
        self,
        user_external_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Conversation], int]:
        """查询会话列表"""
        conditions = [Conversation.tenant_id == self.tenant_id]

        if user_external_id:
            # 先查找用户ID
            user = await self.get_or_create_user(user_external_id)
            conditions.append(Conversation.user_id == user.id)

        if status:
            conditions.append(Conversation.status == status)

        # 查询总数
        count_stmt = select(func.count(Conversation.id)).where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        # 分页查询
        stmt = (
            select(Conversation)
            .where(and_(*conditions))
            .order_by(Conversation.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        return list(conversations), total or 0

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        entities: dict | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> Message:
        """添加消息"""
        conversation = await self.get_conversation(conversation_id)

        # 生成消息ID
        message_id = f"msg_{int(datetime.utcnow().timestamp())}_{conversation.message_count}"

        message = Message(
            tenant_id=self.tenant_id,
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            entities=entities,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        self.db.add(message)

        # 更新会话统计
        conversation.message_count += 1
        if input_tokens:
            conversation.token_usage += input_tokens
        if output_tokens:
            conversation.token_usage += output_tokens

        await self.db.commit()
        await self.db.refresh(message)

        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """获取会话消息"""
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.tenant_id == self.tenant_id,
                    Message.conversation_id == conversation_id,
                )
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def close_conversation(
        self,
        conversation_id: str,
        satisfaction_score: int | None = None,
        feedback: str | None = None,
    ) -> Conversation:
        """关闭会话"""
        conversation = await self.get_conversation(conversation_id)

        conversation.status = "closed"
        conversation.end_time = datetime.utcnow()

        if satisfaction_score:
            conversation.satisfaction_score = satisfaction_score
        if feedback:
            conversation.feedback = feedback

        await self.db.commit()
        await self.db.refresh(conversation)

        return conversation

    async def get_active_conversation_count(self) -> int:
        """获取当前活跃会话数（用于并发检查）"""
        stmt = select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == self.tenant_id,
                Conversation.status == "active",
            )
        )
        count = await self.db.scalar(stmt)
        return count or 0
