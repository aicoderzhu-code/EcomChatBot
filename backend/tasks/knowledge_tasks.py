"""
知识提取相关的 Celery 异步任务
"""
import logging

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.knowledge_tasks.extract_knowledge_from_conversation",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def extract_knowledge_from_conversation(self, tenant_id: str, conversation_id: str):
    """
    异步从对话中提取知识

    在对话关闭且消息数 >= 4 时触发
    """
    import asyncio
    from db.session import get_async_session
    from services.knowledge_extraction_service import KnowledgeExtractionService

    async def _run():
        async with get_async_session() as db:
            service = KnowledgeExtractionService(db, tenant_id)
            candidates = await service.extract_from_conversation(conversation_id)
            logger.info(
                "Extracted %d candidates from conversation %s",
                len(candidates), conversation_id,
            )
            return len(candidates)

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
        logger.error("Knowledge extraction failed: %s", exc)
        raise self.retry(exc=exc)
