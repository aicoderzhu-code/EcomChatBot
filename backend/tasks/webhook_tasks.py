"""
Webhook 后台任务
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from celery import shared_task
from sqlalchemy import and_, select

from db.session import get_sync_session
from models.webhook import WebhookConfig, WebhookLog

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(httpx.TimeoutException, httpx.NetworkError),
)
def send_webhook(
    self,
    webhook_config_id: int,
    event_id: str,
    event_type: str,
    tenant_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    发送 Webhook

    支持自动重试，使用指数退避策略
    """
    with get_sync_session() as db:
        # 获取 Webhook 配置
        stmt = select(WebhookConfig).where(WebhookConfig.id == webhook_config_id)
        result = db.execute(stmt)
        webhook = result.scalar_one_or_none()

        if not webhook:
            logger.error(f"Webhook config {webhook_config_id} not found")
            return {"success": False, "error": "Webhook config not found"}

        if webhook.status != "active":
            logger.info(f"Webhook {webhook_config_id} is not active, skipping")
            return {"success": False, "error": "Webhook is not active"}

        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EcomChatBot-Webhook/1.0",
            "X-Webhook-Event": event_type,
            "X-Webhook-Event-ID": event_id,
            "X-Webhook-Timestamp": str(int(time.time())),
            "X-Webhook-Delivery": str(self.request.retries + 1),
        }

        # 添加签名
        if webhook.secret:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                webhook.secret.encode(),
                payload_str.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # 添加自定义请求头
        if webhook.headers:
            try:
                custom_headers = json.loads(webhook.headers)
                headers.update(custom_headers)
            except json.JSONDecodeError:
                logger.warning(f"Invalid custom headers for webhook {webhook_config_id}")

        # 创建日志记录
        log = WebhookLog(
            webhook_config_id=webhook_config_id,
            tenant_id=tenant_id,
            event_type=event_type,
            event_id=event_id,
            request_url=webhook.url,
            request_headers=json.dumps(headers),
            request_body=json.dumps(payload),
            status="pending",
            attempt_count=self.request.retries + 1,
        )
        db.add(log)
        db.commit()

        # 发送请求
        start_time = time.time()
        try:
            with httpx.Client() as client:
                response = client.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout,
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # 更新日志
            log.response_status = response.status_code
            log.response_headers = json.dumps(dict(response.headers))
            log.response_body = response.text[:10000] if response.text else None
            log.duration_ms = duration_ms

            success = 200 <= response.status_code < 300
            log.status = "success" if success else "failed"

            # 更新 Webhook 状态
            webhook.last_triggered_at = datetime.utcnow()
            if success:
                webhook.failure_count = 0
                webhook.last_success_at = datetime.utcnow()
            else:
                webhook.failure_count += 1
                if webhook.failure_count >= 10:
                    webhook.status = "failed"
                    logger.warning(
                        f"Webhook {webhook_config_id} disabled due to consecutive failures"
                    )

            db.commit()

            if not success and self.request.retries < webhook.retry_count:
                # 计算下次重试时间（指数退避）
                retry_delay = webhook.retry_interval * (2 ** self.request.retries)
                log.status = "retrying"
                log.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                db.commit()

                raise self.retry(countdown=retry_delay)

            return {
                "success": success,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

        except httpx.TimeoutException as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log.status = "failed"
            log.error_message = "请求超时"
            log.duration_ms = duration_ms

            webhook.failure_count += 1
            if webhook.failure_count >= 10:
                webhook.status = "failed"

            db.commit()

            if self.request.retries < webhook.retry_count:
                retry_delay = webhook.retry_interval * (2 ** self.request.retries)
                log.status = "retrying"
                log.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                db.commit()
                raise self.retry(exc=e, countdown=retry_delay)

            return {"success": False, "error": "Timeout"}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log.status = "failed"
            log.error_message = str(e)[:1000]
            log.duration_ms = duration_ms

            webhook.failure_count += 1
            if webhook.failure_count >= 10:
                webhook.status = "failed"

            db.commit()

            logger.error(f"Webhook {webhook_config_id} failed: {e}")
            return {"success": False, "error": str(e)}


@shared_task
def retry_failed_webhooks() -> dict[str, Any]:
    """
    重试失败的 Webhook（定时任务）

    查找所有状态为 retrying 且到达重试时间的日志，
    重新发送
    """
    with get_sync_session() as db:
        # 查找需要重试的日志
        stmt = select(WebhookLog).where(
            and_(
                WebhookLog.status == "retrying",
                WebhookLog.next_retry_at <= datetime.utcnow(),
            )
        )
        result = db.execute(stmt)
        logs = result.scalars().all()

        retried_count = 0
        for log in logs:
            try:
                # 获取原始负载
                payload = json.loads(log.request_body) if log.request_body else {}

                # 重新发送
                send_webhook.delay(
                    webhook_config_id=log.webhook_config_id,
                    event_id=log.event_id,
                    event_type=log.event_type,
                    tenant_id=log.tenant_id,
                    payload=payload,
                )
                retried_count += 1

                # 标记为已处理
                log.status = "pending"
                log.next_retry_at = None

            except Exception as e:
                logger.error(f"Failed to retry webhook log {log.id}: {e}")

        db.commit()

        return {
            "retried_count": retried_count,
            "total_pending": len(logs),
        }


@shared_task
def cleanup_old_webhook_logs(days: int = 30) -> dict[str, Any]:
    """
    清理旧的 Webhook 日志（定时任务）

    删除指定天数之前的日志
    """
    with get_sync_session() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(WebhookLog).where(WebhookLog.created_at < cutoff_date)
        result = db.execute(stmt)
        logs = result.scalars().all()

        deleted_count = len(logs)
        for log in logs:
            db.delete(log)

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old webhook logs")
        return {"deleted_count": deleted_count}
