"""智能触达 Celery 任务"""
import asyncio
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.outreach_tasks.batch_deliver_campaign",
    soft_time_limit=1800,
    time_limit=1860,
)
def batch_deliver_campaign(campaign_id: int, tenant_id: str):
    """批量投递活动下所有待发送任务"""
    asyncio.run(_batch_deliver_campaign(campaign_id, tenant_id))


async def _batch_deliver_campaign(campaign_id: int, tenant_id: str):
    from sqlalchemy import and_, select, update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from models.outreach import OutreachCampaign, OutreachTask
    from services.outreach_delivery_service import OutreachDeliveryService

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as db:
            # 分批获取待发送任务
            batch_size = 100
            offset = 0
            while True:
                stmt = (
                    select(OutreachTask.id)
                    .where(
                        and_(
                            OutreachTask.campaign_id == campaign_id,
                            OutreachTask.status == "pending",
                        )
                    )
                    .order_by(OutreachTask.id)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await db.execute(stmt)
                task_ids = [r[0] for r in result.all()]
                if not task_ids:
                    break

                delivery_service = OutreachDeliveryService(db, tenant_id)
                for task_id in task_ids:
                    try:
                        await delivery_service.deliver_task(task_id)
                        await db.commit()
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"任务 {task_id} 投递失败: {e}")

                offset += batch_size

            # 检查是否全部完成
            async with session_factory() as db:
                pending = (await db.execute(
                    select(OutreachTask.id).where(
                        and_(
                            OutreachTask.campaign_id == campaign_id,
                            OutreachTask.status.in_(["pending", "generating", "sending"]),
                        )
                    ).limit(1)
                )).scalar()

                if not pending:
                    from datetime import datetime
                    await db.execute(
                        update(OutreachCampaign)
                        .where(OutreachCampaign.id == campaign_id)
                        .values(status="completed", completed_at=datetime.utcnow())
                    )
                    await db.commit()

    finally:
        await engine.dispose()


@celery_app.task(
    name="tasks.outreach_tasks.deliver_outreach_task",
    soft_time_limit=120,
    time_limit=150,
    bind=True,
    max_retries=3,
)
def deliver_outreach_task(self, task_id: int, tenant_id: str):
    """执行单条触达任务"""
    try:
        asyncio.run(_deliver_single_task(task_id, tenant_id))
    except Exception as e:
        logger.error(f"触达任务 {task_id} 失败: {e}")
        self.retry(exc=e, countdown=60 * (self.request.retries + 1))


async def _deliver_single_task(task_id: int, tenant_id: str):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from services.outreach_delivery_service import OutreachDeliveryService

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            service = OutreachDeliveryService(db, tenant_id)
            await service.deliver_task(task_id)
            await db.commit()
    finally:
        await engine.dispose()


@celery_app.task(
    name="tasks.outreach_tasks.evaluate_auto_rules",
    soft_time_limit=300,
    time_limit=360,
)
def evaluate_auto_rules():
    """评估所有租户的自动触发规则"""
    asyncio.run(_evaluate_auto_rules())


async def _evaluate_auto_rules():
    from sqlalchemy import distinct, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from models.outreach import OutreachRule
    from services.outreach_rule_service import OutreachRuleService

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            # 获取所有有活跃规则的租户
            stmt = select(distinct(OutreachRule.tenant_id)).where(OutreachRule.is_active == 1)
            result = await db.execute(stmt)
            tenant_ids = [r[0] for r in result.all()]

        for tid in tenant_ids:
            try:
                async with session_factory() as db:
                    service = OutreachRuleService(db, tid)
                    count = await service.evaluate_rules()
                    await db.commit()
                    if count:
                        logger.info(f"租户 {tid} 自动规则触发 {count} 条任务")
            except Exception as e:
                logger.error(f"租户 {tid} 规则评估失败: {e}")
    finally:
        await engine.dispose()


@celery_app.task(
    name="tasks.outreach_tasks.process_follow_ups",
    soft_time_limit=300,
    time_limit=360,
)
def process_follow_ups():
    """处理所有租户的到期跟进计划"""
    asyncio.run(_process_follow_ups())


async def _process_follow_ups():
    from sqlalchemy import distinct, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from models.follow_up import FollowUpPlan
    from services.follow_up_service import FollowUpService

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            stmt = select(distinct(FollowUpPlan.tenant_id)).where(FollowUpPlan.status == "active")
            result = await db.execute(stmt)
            tenant_ids = [r[0] for r in result.all()]

        for tid in tenant_ids:
            try:
                async with session_factory() as db:
                    service = FollowUpService(db, tid)
                    count = await service.process_due_follow_ups()
                    await db.commit()
                    if count:
                        logger.info(f"租户 {tid} 执行 {count} 条跟进")
            except Exception as e:
                logger.error(f"租户 {tid} 跟进处理失败: {e}")
    finally:
        await engine.dispose()


@celery_app.task(
    name="tasks.outreach_tasks.refresh_dynamic_segments",
    soft_time_limit=600,
    time_limit=660,
)
def refresh_dynamic_segments():
    """刷新所有动态分群"""
    asyncio.run(_refresh_dynamic_segments())


async def _refresh_dynamic_segments():
    from sqlalchemy import and_, distinct, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from models.customer_segment import CustomerSegment
    from services.customer_segment_service import CustomerSegmentService

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            stmt = select(CustomerSegment.id, CustomerSegment.tenant_id).where(
                and_(
                    CustomerSegment.segment_type == "dynamic",
                    CustomerSegment.is_active == 1,
                )
            )
            result = await db.execute(stmt)
            segments = result.all()

        for seg_id, tid in segments:
            try:
                async with session_factory() as db:
                    service = CustomerSegmentService(db, tid)
                    await service.refresh_segment_members(seg_id)
                    await db.commit()
                    logger.info(f"刷新动态分群 {seg_id}")
            except Exception as e:
                logger.error(f"刷新分群 {seg_id} 失败: {e}")
    finally:
        await engine.dispose()


@celery_app.task(
    name="tasks.outreach_tasks.process_post_purchase_recommendations",
    soft_time_limit=120,
    time_limit=150,
)
def process_post_purchase_recommendations(order_id: int, tenant_id: str):
    """订单完成后处理增购推荐"""
    asyncio.run(_process_post_purchase(order_id, tenant_id))


async def _process_post_purchase(order_id: int, tenant_id: str):
    from sqlalchemy import and_, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from core.config import settings
    from models.order import Order
    from models.conversation import User
    from services.recommendation_engine import RecommendationEngine

    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            # 获取订单的用户ID
            order = (await db.execute(
                select(Order).where(and_(Order.id == order_id, Order.tenant_id == tenant_id))
            )).scalar_one_or_none()
            if not order:
                return

            user = (await db.execute(
                select(User).where(
                    and_(User.tenant_id == tenant_id, User.platform_user_id == order.buyer_id)
                )
            )).scalar_one_or_none()
            if not user:
                return

            engine_service = RecommendationEngine(db, tenant_id)
            await engine_service.get_post_purchase_recommendations(user.id, order_id)
            await db.commit()
    finally:
        await engine.dispose()
