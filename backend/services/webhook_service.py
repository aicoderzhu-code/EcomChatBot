"""
Webhook管理服务
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any
import httpx

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.webhook import WebhookConfig, WebhookLog, WebhookEventType
from core.exceptions import AppException


class WebhookService:
    """Webhook管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def create_webhook(
        self,
        name: str,
        endpoint_url: str,
        events: list[str],
        secret: str | None = None
    ) -> WebhookConfig:
        """
        创建Webhook配置

        Args:
            name: 配置名称
            endpoint_url: Webhook URL
            events: 监听的事件列表
            secret: 签名密钥（可选）

        Returns:
            WebhookConfig
        """
        # 验证事件类型
        valid_events = [e.value for e in WebhookEventType]
        for event in events:
            if event not in valid_events:
                raise AppException(f"无效的事件类型: {event}")

        # 如果没有提供secret，自动生成
        if not secret:
            import secrets
            secret = secrets.token_urlsafe(32)

        webhook = WebhookConfig(
            tenant_id=self.tenant_id,
            name=name,
            endpoint_url=endpoint_url,
            events=events,
            secret=secret,
            is_active=True
        )

        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)

        return webhook

    async def get_webhook(self, webhook_id: int) -> WebhookConfig:
        """获取Webhook配置"""
        stmt = select(WebhookConfig).where(
            and_(
                WebhookConfig.id == webhook_id,
                WebhookConfig.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        webhook = result.scalar_one_or_none()

        if not webhook:
            raise AppException("Webhook配置不存在")

        return webhook

    async def list_webhooks(self) -> list[WebhookConfig]:
        """列出所有Webhook配置"""
        stmt = select(WebhookConfig).where(
            WebhookConfig.tenant_id == self.tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_webhook(
        self,
        webhook_id: int,
        name: str | None = None,
        endpoint_url: str | None = None,
        events: list[str] | None = None,
        is_active: bool | None = None
    ) -> WebhookConfig:
        """更新Webhook配置"""
        webhook = await self.get_webhook(webhook_id)

        if name is not None:
            webhook.name = name
        if endpoint_url is not None:
            webhook.endpoint_url = endpoint_url
        if events is not None:
            # 验证事件类型
            valid_events = [e.value for e in WebhookEventType]
            for event in events:
                if event not in valid_events:
                    raise AppException(f"无效的事件类型: {event}")
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active

        await self.db.commit()
        await self.db.refresh(webhook)

        return webhook

    async def delete_webhook(self, webhook_id: int) -> bool:
        """删除Webhook配置"""
        webhook = await self.get_webhook(webhook_id)
        await self.db.delete(webhook)
        await self.db.commit()
        return True

    async def get_webhook_logs(
        self,
        webhook_id: int | None = None,
        limit: int = 50
    ) -> list[WebhookLog]:
        """获取Webhook日志"""
        conditions = [WebhookLog.tenant_id == self.tenant_id]

        if webhook_id:
            conditions.append(WebhookLog.webhook_config_id == webhook_id)

        stmt = select(WebhookLog).where(
            *conditions
        ).order_by(WebhookLog.created_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    def generate_signature(self, payload: dict, secret: str) -> str:
        """
        生成Webhook签名

        Args:
            payload: 请求payload
            secret: 密钥

        Returns:
            签名字符串
        """
        # 将payload转换为JSON字符串
        payload_str = json.dumps(payload, sort_keys=True)

        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def send_webhook(
        self,
        webhook: WebhookConfig,
        event_type: str,
        event_data: dict
    ) -> WebhookLog:
        """
        发送Webhook请求

        Args:
            webhook: Webhook配置
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            WebhookLog
        """
        # 生成事件ID
        event_id = str(uuid.uuid4())

        # 构建payload
        payload = {
            "id": event_id,
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": event_data
        }

        # 创建日志记录
        log = WebhookLog(
            tenant_id=self.tenant_id,
            webhook_config_id=webhook.id,
            event_type=event_type,
            event_id=event_id,
            request_payload=payload,
            status="pending",
            retry_count=0
        )

        try:
            # 生成签名
            if webhook.secret:
                signature = self.generate_signature(payload, webhook.secret)
                headers = {
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Timestamp": payload["timestamp"],
                    "X-Webhook-Event": event_type,
                    "Content-Type": "application/json"
                }
            else:
                headers = {
                    "Content-Type": "application/json"
                }

            # 发送HTTP请求
            start_time = datetime.utcnow()

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.endpoint_url,
                    json=payload,
                    headers=headers
                )

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # 更新日志
            log.response_status = response.status_code
            log.response_body = response.text[:1000]  # 限制长度
            log.status = "success" if response.status_code < 400 else "failed"
            log.processed_at = end_time
            log.duration_ms = duration_ms

            # 更新webhook统计
            webhook.total_calls += 1
            webhook.last_called_at = end_time
            webhook.last_status = log.status

            if log.status == "success":
                webhook.success_calls += 1
            else:
                webhook.failed_calls += 1

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.processed_at = datetime.utcnow()

            webhook.total_calls += 1
            webhook.failed_calls += 1
            webhook.last_called_at = log.processed_at
            webhook.last_status = "failed"

        self.db.add(log)
        await self.db.commit()

        return log

    async def trigger_event(
        self,
        event_type: str,
        event_data: dict
    ) -> list[WebhookLog]:
        """
        触发事件，发送到所有匹配的Webhook

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            发送结果列表
        """
        # 查询所有激活的webhook配置
        stmt = select(WebhookConfig).where(
            and_(
                WebhookConfig.tenant_id == self.tenant_id,
                WebhookConfig.is_active == True,
                WebhookConfig.events.contains([event_type])  # JSON包含查询
            )
        )
        result = await self.db.execute(stmt)
        webhooks = result.scalars().all()

        logs = []
        for webhook in webhooks:
            try:
                log = await self.send_webhook(webhook, event_type, event_data)
                logs.append(log)
            except Exception as e:
                # 记录失败但继续处理其他webhook
                continue

        return logs

    async def verify_webhook_signature(
        self,
        payload: dict,
        signature: str,
        secret: str
    ) -> bool:
        """
        验证Webhook签名

        Args:
            payload: 请求payload
            signature: 请求头中的签名
            secret: webhook密钥

        Returns:
            是否验证通过
        """
        expected_signature = self.generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)
