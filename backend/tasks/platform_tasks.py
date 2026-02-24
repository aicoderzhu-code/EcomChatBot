"""
平台对接定时任务
"""
import logging
from datetime import datetime, timedelta

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.platform_tasks.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """刷新即将过期的平台 access_token（提前 1 天刷新）"""
    import asyncio
    asyncio.run(_refresh_expiring_tokens())


async def _refresh_expiring_tokens():
    from sqlalchemy import and_, select
    from db import get_db
    from models.platform import PlatformConfig
    from services.platform.pinduoduo_client import PinduoduoClient

    threshold = datetime.utcnow() + timedelta(days=1)

    async for db in get_db():
        stmt = select(PlatformConfig).where(
            and_(
                PlatformConfig.is_active == True,
                PlatformConfig.refresh_token.isnot(None),
                PlatformConfig.expires_at <= threshold,
            )
        )
        result = await db.execute(stmt)
        configs = result.scalars().all()

        for config in configs:
            try:
                client = PinduoduoClient(config.app_key, config.app_secret)
                token_data = await client.refresh_access_token(config.refresh_token)
                new_token = token_data.get("access_token")
                new_refresh = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 7776000)

                if new_token:
                    config.access_token = new_token
                    config.refresh_token = new_refresh or config.refresh_token
                    config.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    await db.commit()
                    logger.info(
                        "已刷新 tenant=%s platform=%s 的 access_token",
                        config.tenant_id,
                        config.platform_type,
                    )
            except Exception as e:
                logger.error(
                    "刷新 token 失败 tenant=%s: %s",
                    config.tenant_id,
                    e,
                )
