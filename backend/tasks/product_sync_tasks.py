"""商品同步 Celery 任务"""
import asyncio
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.product_sync_tasks.run_product_sync",
    soft_time_limit=1800,
    time_limit=1860,
)
def run_product_sync(task_id: int, tenant_id: str):
    """执行商品同步任务"""
    asyncio.run(_run_product_sync(task_id, tenant_id))


async def _run_product_sync(task_id: int, tenant_id: str):
    from db.session import get_async_session
    from services.product_sync_service import ProductSyncService

    async with get_async_session() as db:
        service = ProductSyncService(db, tenant_id)
        await service.execute_sync(task_id)


@celery_app.task(name="tasks.product_sync_tasks.run_scheduled_syncs")
def run_scheduled_syncs():
    """执行所有到期的定时同步任务"""
    asyncio.run(_run_scheduled_syncs())


async def _run_scheduled_syncs():
    from datetime import datetime
    from sqlalchemy import and_, select
    from db.session import get_async_session
    from models.product import ProductSyncSchedule
    from services.product_sync_service import ProductSyncService

    async with get_async_session() as db:
        now = datetime.utcnow()
        stmt = select(ProductSyncSchedule).where(
            and_(
                ProductSyncSchedule.is_active == 1,
                ProductSyncSchedule.next_run_at <= now,
            )
        )
        result = await db.execute(stmt)
        schedules = list(result.scalars().all())

        for schedule in schedules:
            try:
                service = ProductSyncService(db, schedule.tenant_id)
                task = await service.trigger_sync(
                    platform_config_id=schedule.platform_config_id,
                    sync_type="incremental",
                )
                # 异步执行同步
                run_product_sync.delay(task.id, schedule.tenant_id)
                logger.info(
                    "触发增量同步: tenant=%s, platform=%d",
                    schedule.tenant_id, schedule.platform_config_id,
                )
            except ValueError as e:
                logger.warning("跳过同步: %s", e)
            except Exception:
                logger.exception(
                    "触发定时同步失败: tenant=%s", schedule.tenant_id
                )
