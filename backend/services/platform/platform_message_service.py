"""
平台消息处理服务
处理来自电商平台（拼多多等）的 Webhook 消息
"""
import logging
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import generate_conversation_id
from models import Conversation, Message, User
from models.platform import PlatformConfig
from services.conversation_service import ConversationService
from services.platform.pinduoduo_client import PinduoduoClient

logger = logging.getLogger(__name__)


class PlatformMessageService:
    """平台消息处理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_platform_config(
        self, platform_type: str, shop_id: str
    ) -> PlatformConfig | None:
        """通过 shop_id 查找平台配置"""
        stmt = select(PlatformConfig).where(
            and_(
                PlatformConfig.platform_type == platform_type,
                PlatformConfig.shop_id == shop_id,
                PlatformConfig.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def handle_pinduoduo_webhook(self, payload: dict) -> None:
        """
        处理拼多多 Webhook 推送

        payload 字段（参考 POP 文档）：
          - shop_id: 店铺ID
          - buyer_id: 买家ID
          - conversation_id: 拼多多会话ID
          - content: 消息内容
          - msg_type: 消息类型（1=文本）
        """
        shop_id = str(payload.get("shop_id", ""))
        buyer_id = str(payload.get("buyer_id", ""))
        pdd_conversation_id = str(payload.get("conversation_id", ""))
        content = payload.get("content", "")
        msg_type = payload.get("msg_type", 1)

        # 只处理文本消息
        if msg_type != 1 or not content:
            return

        # 1. 查找平台配置 → 获取 tenant_id
        config = await self._get_platform_config("pinduoduo", shop_id)
        if not config:
            logger.warning("未找到 shop_id=%s 对应的平台配置", shop_id)
            return

        tenant_id = config.tenant_id

        # 2. 查找或创建用户
        conv_service = ConversationService(self.db, tenant_id)
        user_external_id = f"pdd_{buyer_id}"
        user = await conv_service.get_or_create_user(
            user_external_id=user_external_id,
            user_data={"nickname": f"拼多多买家{buyer_id}"},
        )
        # 记录平台用户ID
        if not user.platform_user_id:
            user.platform_user_id = buyer_id
            await self.db.commit()

        # 3. 查找或创建会话
        conversation = await self._get_or_create_platform_conversation(
            tenant_id=tenant_id,
            user_id=user.id,
            platform_type="pinduoduo",
            platform_conversation_id=pdd_conversation_id,
        )

        # 4. 保存用户消息
        msg_id = f"msg_{int(datetime.utcnow().timestamp())}_{buyer_id}"
        message = Message(
            tenant_id=tenant_id,
            message_id=msg_id,
            conversation_id=conversation.conversation_id,
            role="user",
            content=content,
        )
        self.db.add(message)
        await self.db.commit()

        # 5. 意图识别
        from services.intent_service import IntentService
        intent_service = IntentService(db=self.db, tenant_id=tenant_id)
        intent = intent_service.classify_intent_by_rules(content)
        confidence = intent_service.get_intent_confidence(content, intent)

        # 6. 根据置信度决定 AI 回复还是转人工
        threshold = config.auto_reply_threshold
        if confidence >= threshold:
            await self._ai_reply(
                db=self.db,
                tenant_id=tenant_id,
                conversation=conversation,
                user_input=content,
                config=config,
            )
        else:
            await self._escalate_to_human(
                db=self.db,
                tenant_id=tenant_id,
                conversation=conversation,
                config=config,
            )

    async def _get_or_create_platform_conversation(
        self,
        tenant_id: str,
        user_id: int,
        platform_type: str,
        platform_conversation_id: str,
    ) -> Conversation:
        """查找或创建平台会话"""
        stmt = select(Conversation).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.platform_type == platform_type,
                Conversation.platform_conversation_id == platform_conversation_id,
                Conversation.status == "active",
            )
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                tenant_id=tenant_id,
                conversation_id=generate_conversation_id(),
                user_id=user_id,
                channel="pinduoduo",
                platform_type=platform_type,
                platform_conversation_id=platform_conversation_id,
                status="active",
                start_time=datetime.utcnow(),
            )
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)

        return conversation

    async def _ai_reply(
        self,
        db: AsyncSession,
        tenant_id: str,
        conversation: Conversation,
        user_input: str,
        config: PlatformConfig,
    ) -> None:
        """调用 AI 生成回复并发送到拼多多"""
        try:
            from services.conversation_chain_service import ConversationChainService
            chain = ConversationChainService(
                db=db,
                tenant_id=tenant_id,
                conversation_id=conversation.conversation_id,
                platform_name="拼多多",
            )
            await chain.initialize()
            result = await chain.chat(user_input=user_input)
            reply_text = result["response"]

            # 发送到拼多多
            client = PinduoduoClient(config.app_key, config.app_secret)
            await client.send_message(
                access_token=config.access_token,
                conversation_id=conversation.platform_conversation_id,
                content=reply_text,
            )

            # 保存 AI 回复消息
            ai_msg_id = f"msg_{int(datetime.utcnow().timestamp())}_ai"
            ai_msg = Message(
                tenant_id=tenant_id,
                message_id=ai_msg_id,
                conversation_id=conversation.conversation_id,
                role="assistant",
                content=reply_text,
                input_tokens=result.get("input_tokens"),
                output_tokens=result.get("output_tokens"),
            )
            db.add(ai_msg)
            await db.commit()
        except Exception as e:
            logger.error("AI 回复失败: %s", e, exc_info=True)

    async def _escalate_to_human(
        self,
        db: AsyncSession,
        tenant_id: str,
        conversation: Conversation,
        config: PlatformConfig,
    ) -> None:
        """标记转人工并通知租户"""
        conversation.status = "pending_human"
        conversation.transferred_to_human = True
        conversation.transfer_reason = "AI 置信度不足"
        await db.commit()

        # 发送转人工提示语给买家
        if config.human_takeover_message and config.access_token:
            try:
                client = PinduoduoClient(config.app_key, config.app_secret)
                await client.send_message(
                    access_token=config.access_token,
                    conversation_id=conversation.platform_conversation_id,
                    content=config.human_takeover_message,
                )
            except Exception as e:
                logger.warning("发送转人工提示语失败: %s", e)

        # 触发 Webhook 通知租户
        try:
            from services.webhook_service import WebhookService
            webhook_service = WebhookService(db, tenant_id)
            await webhook_service.trigger_event(
                event_type="conversation.human_required",
                event_data={
                    "conversation_id": conversation.conversation_id,
                    "platform_type": conversation.platform_type,
                    "platform_conversation_id": conversation.platform_conversation_id,
                },
            )
        except Exception as e:
            logger.warning("触发 Webhook 通知失败: %s", e)
