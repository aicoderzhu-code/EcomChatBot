"""内容生成 Celery 任务"""
import asyncio
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.generation_tasks.run_generation",
    soft_time_limit=600,
    time_limit=660,
)
def run_generation(task_id: int, tenant_id: str):
    """执行内容生成任务"""
    asyncio.run(_run_generation(task_id, tenant_id))


async def _run_generation(task_id: int, tenant_id: str):
    from db.session import get_async_session
    from services.content_generation.generation_service import GenerationService

    async with get_async_session() as db:
        service = GenerationService(db, tenant_id)
        await service.execute_task(task_id)
