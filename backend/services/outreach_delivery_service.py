"""外呼投递服务 — 频率控制 + 内容生成 + 平台消息发送"""
import logging
from datetime import datetime, date

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import User
from models.outreach import OutreachCampaign, OutreachTask

logger = logging.getLogger(__name__)


class OutreachDeliveryService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def deliver_task(self, task_id: int) -> bool:
        """执行单条触达任务的完整流程"""
        # 获取任务
        stmt = select(OutreachTask).where(
            and_(OutreachTask.id == task_id, OutreachTask.tenant_id == self.tenant_id)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task or task.status not in ("pending", "generating"):
            return False

        try:
            # 1. 频率控制
            campaign = None
            max_per_day = 3
            if task.campaign_id:
                camp_stmt = select(OutreachCampaign).where(OutreachCampaign.id == task.campaign_id)
                camp_result = await self.db.execute(camp_stmt)
                campaign = camp_result.scalar_one_or_none()
                if campaign:
                    max_per_day = campaign.max_per_user_per_day

            if not await self._check_rate_limit(task.user_id, max_per_day):
                task.status = "cancelled"
                task.error_message = "超过每日触达限制"
                await self.db.flush()
                return False

            # 2. 获取用户信息
            user_stmt = select(User).where(User.id == task.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if not user:
                task.status = "failed"
                task.error_message = "用户不存在"
                await self.db.flush()
                return False

            user_dict = {
                "nickname": user.nickname or "客户",
                "vip_level": user.vip_level,
                "user_external_id": user.user_external_id,
                "platform_user_id": user.platform_user_id,
            }

            # 3. 生成内容
            if not task.content:
                task.status = "generating"
                await self.db.flush()

                from services.outreach_content_service import OutreachContentService
                content_service = OutreachContentService(self.db, self.tenant_id)

                strategy = "template"
                template = None
                ai_prompt = None
                context = {}

                if campaign:
                    strategy = campaign.content_strategy
                    template = campaign.content_template
                    ai_prompt = campaign.ai_prompt

                if task.follow_up_plan_id:
                    context["follow_up_sequence"] = task.follow_up_sequence or 1

                # 获取关联商品
                related_products = []
                if task.related_product_ids:
                    from models.product import Product
                    prod_stmt = select(Product).where(Product.id.in_(task.related_product_ids))
                    prod_result = await self.db.execute(prod_stmt)
                    related_products = [
                        {"title": p.title, "price": float(p.price)} for p in prod_result.scalars().all()
                    ]

                task.content = await content_service.generate_content(
                    user=user_dict,
                    strategy=strategy,
                    template=template,
                    ai_prompt=ai_prompt,
                    related_products=related_products,
                    context=context,
                )
                task.content_generated_at = datetime.utcnow()

            # 4. 发送消息
            task.status = "sending"
            await self.db.flush()

            sent = await self._send_platform_message(task, user)
            if sent:
                task.status = "sent"
                task.sent_at = datetime.utcnow()
                # 更新活动统计
                if task.campaign_id:
                    await self.db.execute(
                        update(OutreachCampaign)
                        .where(OutreachCampaign.id == task.campaign_id)
                        .values(sent_count=OutreachCampaign.sent_count + 1)
                    )
                # 增加 Redis 计数
                await self._increment_rate_count(task.user_id)
            else:
                task.status = "failed"
                task.error_message = "平台消息发送失败"
                if task.campaign_id:
                    await self.db.execute(
                        update(OutreachCampaign)
                        .where(OutreachCampaign.id == task.campaign_id)
                        .values(failed_count=OutreachCampaign.failed_count + 1)
                    )

            await self.db.flush()
            return sent

        except Exception as e:
            logger.error(f"触达任务 {task_id} 投递失败: {e}")
            task.status = "failed"
            task.error_message = str(e)[:500]
            if task.campaign_id:
                await self.db.execute(
                    update(OutreachCampaign)
                    .where(OutreachCampaign.id == task.campaign_id)
                    .values(failed_count=OutreachCampaign.failed_count + 1)
                )
            await self.db.flush()
            return False

    async def _check_rate_limit(self, user_id: int, max_per_day: int) -> bool:
        """检查频率限制"""
        try:
            from db.redis import get_redis
            redis = await get_redis()
            key = f"outreach:rate:{self.tenant_id}:{user_id}:{date.today().isoformat()}"
            count = await redis.get(key)
            if count and int(count) >= max_per_day:
                return False
            return True
        except Exception as e:
            logger.warning(f"Redis 频率检查失败，默认放行: {e}")
            return True

    async def _increment_rate_count(self, user_id: int) -> None:
        """增加频率计数"""
        try:
            from db.redis import get_redis
            redis = await get_redis()
            key = f"outreach:rate:{self.tenant_id}:{user_id}:{date.today().isoformat()}"
            await redis.incr(key)
            await redis.expire(key, 86400)  # 24h TTL
        except Exception as e:
            logger.warning(f"Redis 频率计数失败: {e}")

    async def _send_platform_message(self, task: OutreachTask, user: User) -> bool:
        """通过平台客户端发送消息"""
        if not task.platform_config_id:
            logger.warning(f"任务 {task.id} 未配置平台，跳过发送")
            return False

        try:
            from services.platform.platform_message_service import PlatformMessageService
            msg_service = PlatformMessageService(self.db)

            # 查找或创建会话
            conversation_id = task.platform_conversation_id
            if not conversation_id and user.platform_user_id:
                # 尝试查找现有会话
                from models.conversation import Conversation
                conv_stmt = select(Conversation).where(
                    and_(
                        Conversation.tenant_id == self.tenant_id,
                        Conversation.user_external_id == user.user_external_id,
                        Conversation.status != "closed",
                    )
                ).order_by(Conversation.id.desc()).limit(1)
                conv_result = await self.db.execute(conv_stmt)
                conv = conv_result.scalar_one_or_none()
                if conv:
                    conversation_id = conv.conversation_id

            if conversation_id:
                await msg_service.send_outbound_message(
                    platform_config_id=task.platform_config_id,
                    conversation_id=conversation_id,
                    content=task.content,
                )
                return True
            else:
                logger.warning(f"任务 {task.id} 找不到会话，无法发送")
                return False

        except Exception as e:
            logger.error(f"平台消息发送失败: {e}")
            return False
