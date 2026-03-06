"""Webhook 事件记录模型"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class WebhookEvent(TenantBaseModel):
    """Webhook 事件记录（消息可靠性保障）"""

    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("idx_webhook_event_id", "event_id", unique=True),
        Index("idx_webhook_event_status", "status"),
        Index("idx_webhook_event_platform", "platform_type", "platform_config_id"),
        {"comment": "Webhook 事件记录表"},
    )

    event_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="唯一事件ID(幂等键)")
    platform_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="来源平台")
    platform_config_id: Mapped[int | None] = mapped_column(Integer, comment="关联平台配置ID")

    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="事件类型(message/order_status/aftersale/product_change)"
    )
    payload: Mapped[dict | None] = mapped_column(JSON, comment="原始事件数据")

    status: Mapped[str] = mapped_column(
        String(16), default="received",
        comment="处理状态(received/processing/processed/failed)"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    error_message: Mapped[str | None] = mapped_column(Text, comment="失败原因")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="处理完成时间")

    def __repr__(self) -> str:
        return f"<WebhookEvent {self.event_id} ({self.status})>"
