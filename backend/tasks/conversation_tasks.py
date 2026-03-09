"""
对话相关的 Celery 异步任务
"""
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.conversation_tasks.generate_conversation_summary",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_conversation_summary(self, tenant_id: str, conversation_id: str):
    """
    异步生成对话摘要

    在对话关闭时触发
    """
    import asyncio
    from db.session import get_async_session
    from services.conversation_summary_service import ConversationSummaryService

    async def _run():
        async with get_async_session() as db:
            service = ConversationSummaryService(db, tenant_id)
            summary = await service.generate_summary(conversation_id)
            logger.info(
                "Generated summary for conversation %s: %s...",
                conversation_id,
                summary[:50] if summary else "empty",
            )
            return summary

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run())
                return future.result()
        else:
            return asyncio.run(_run())
    except Exception as exc:
        logger.error("Summary generation failed: %s", exc)
        raise self.retry(exc=exc)
