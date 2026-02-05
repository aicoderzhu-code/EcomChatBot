"""
Webhook 事件发布器
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.webhook import WebhookConfig
from services.webhook.events import WebhookEvent, WebhookEventType

logger = logging.getLogger(__name__)


class WebhookPublisher:
    """Webhook 事件发布器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def publish(self, event: WebhookEvent) -> None:
        """
        发布 Webhook 事件

        查找订阅该事件类型的所有活跃 Webhook 配置，
        并为每个配置创建异步任务发送 Webhook
        """
        # 查找订阅该事件类型的活跃 Webhook 配置
        stmt = select(WebhookConfig).where(
            WebhookConfig.tenant_id == event.tenant_id,
            WebhookConfig.event_type == event.event_type.value,
            WebhookConfig.status == "active",
        )
        result = await self.db.execute(stmt)
        webhook_configs = result.scalars().all()

        if not webhook_configs:
            logger.debug(
                f"No active webhooks for event {event.event_type.value} "
                f"in tenant {event.tenant_id}"
            )
            return

        # 为每个 Webhook 配置创建发送任务
        for config in webhook_configs:
            try:
                from tasks.webhook_tasks import send_webhook

                # 异步发送 Webhook
                send_webhook.delay(
                    webhook_config_id=config.id,
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    tenant_id=event.tenant_id,
                    payload=event.to_payload(),
                )
                logger.info(
                    f"Queued webhook {config.id} for event {event.event_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to queue webhook {config.id}: {e}"
                )

    async def publish_conversation_created(
        self,
        tenant_id: str,
        conversation_id: str,
        user_id: str | None = None,
        channel: str | None = None,
    ) -> None:
        """发布会话创建事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.CONVERSATION_CREATED,
            tenant_id=tenant_id,
            data={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "channel": channel,
            },
        )
        await self.publish(event)

    async def publish_conversation_closed(
        self,
        tenant_id: str,
        conversation_id: str,
        close_reason: str | None = None,
    ) -> None:
        """发布会话关闭事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.CONVERSATION_CLOSED,
            tenant_id=tenant_id,
            data={
                "conversation_id": conversation_id,
                "close_reason": close_reason,
            },
        )
        await self.publish(event)

    async def publish_message_received(
        self,
        tenant_id: str,
        conversation_id: str,
        message_id: str,
        content: str,
        user_id: str | None = None,
    ) -> None:
        """发布消息接收事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.MESSAGE_RECEIVED,
            tenant_id=tenant_id,
            data={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "content": content[:500],  # 截断长消息
                "user_id": user_id,
            },
        )
        await self.publish(event)

    async def publish_message_sent(
        self,
        tenant_id: str,
        conversation_id: str,
        message_id: str,
        content: str,
    ) -> None:
        """发布消息发送事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.MESSAGE_SENT,
            tenant_id=tenant_id,
            data={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "content": content[:500],  # 截断长消息
            },
        )
        await self.publish(event)

    async def publish_user_created(
        self,
        tenant_id: str,
        user_id: str,
        external_id: str | None = None,
    ) -> None:
        """发布用户创建事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.USER_CREATED,
            tenant_id=tenant_id,
            data={
                "user_id": user_id,
                "external_id": external_id,
            },
        )
        await self.publish(event)

    async def publish_subscription_created(
        self,
        tenant_id: str,
        subscription_id: int,
        plan_type: str,
        expire_at: str,
    ) -> None:
        """发布订阅创建事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.SUBSCRIPTION_CREATED,
            tenant_id=tenant_id,
            data={
                "subscription_id": subscription_id,
                "plan_type": plan_type,
                "expire_at": expire_at,
            },
        )
        await self.publish(event)

    async def publish_subscription_updated(
        self,
        tenant_id: str,
        subscription_id: int,
        old_plan: str,
        new_plan: str,
    ) -> None:
        """发布订阅更新事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.SUBSCRIPTION_UPDATED,
            tenant_id=tenant_id,
            data={
                "subscription_id": subscription_id,
                "old_plan": old_plan,
                "new_plan": new_plan,
            },
        )
        await self.publish(event)

    async def publish_subscription_expired(
        self,
        tenant_id: str,
        subscription_id: int,
        plan_type: str,
    ) -> None:
        """发布订阅过期事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.SUBSCRIPTION_EXPIRED,
            tenant_id=tenant_id,
            data={
                "subscription_id": subscription_id,
                "plan_type": plan_type,
            },
        )
        await self.publish(event)

    async def publish_quota_warning(
        self,
        tenant_id: str,
        quota_type: str,
        used: int,
        limit: int,
        percentage: float,
    ) -> None:
        """发布配额警告事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.QUOTA_WARNING,
            tenant_id=tenant_id,
            data={
                "quota_type": quota_type,
                "used": used,
                "limit": limit,
                "percentage": percentage,
            },
        )
        await self.publish(event)

    async def publish_quota_exceeded(
        self,
        tenant_id: str,
        quota_type: str,
        used: int,
        limit: int,
    ) -> None:
        """发布配额超限事件"""
        event = WebhookEvent(
            event_type=WebhookEventType.QUOTA_EXCEEDED,
            tenant_id=tenant_id,
            data={
                "quota_type": quota_type,
                "used": used,
                "limit": limit,
            },
        )
        await self.publish(event)
