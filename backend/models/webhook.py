"""
Webhook相关数据模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TenantBaseModel


class WebhookEventType(str, Enum):
    """Webhook事件类型"""
    # 对话事件
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    CONVERSATION_TRANSFERRED = "conversation.transferred"

    # 消息事件
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"

    # 满意度事件
    SATISFACTION_RATED = "satisfaction.rated"

    # 配额事件
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"

    # 订阅事件
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    SUBSCRIPTION_EXPIRED = "subscription.expired"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"

    # 支付事件
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"


class WebhookConfig(TenantBaseModel):
    """Webhook配置表"""
    __tablename__ = "webhook_configs"
    __table_args__ = (
        Index("idx_webhook_tenant", "tenant_id"),
        Index("idx_webhook_status", "is_active"),
        {"comment": "Webhook配置表"},
    )

    # 配置信息
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="配置名称"
    )
    endpoint_url: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Webhook URL"
    )

    # 事件过滤
    events: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, comment="监听的事件列表"
    )

    # 安全配置
    secret: Mapped[str | None] = mapped_column(
        String(128), comment="Webhook密钥（用于签名验证）"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否激活"
    )

    # 统计信息
    total_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="总调用次数"
    )
    success_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="成功次数"
    )
    failed_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="失败次数"
    )

    # 最后调用信息
    last_called_at: Mapped[datetime | None] = mapped_column(
        comment="最后调用时间"
    )
    last_status: Mapped[str | None] = mapped_column(
        String(32), comment="最后调用状态(success/failed)"
    )

    # 关联关系
    logs: Mapped[list["WebhookLog"]] = relationship(
        "WebhookLog", back_populates="config", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<WebhookConfig {self.name}>"


class WebhookLog(TenantBaseModel):
    """Webhook调用日志表"""
    __tablename__ = "webhook_logs"
    __table_args__ = (
        Index("idx_webhook_log_config", "webhook_config_id"),
        Index("idx_webhook_log_tenant", "tenant_id"),
        Index("idx_webhook_log_event", "event_type"),
        Index("idx_webhook_log_created", "created_at"),
        {"comment": "Webhook调用日志表"},
    )

    # 关联配置
    webhook_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhook_configs.id"), nullable=False, comment="Webhook配置ID"
    )

    # 事件信息
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="事件类型"
    )
    event_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="事件ID"
    )

    # 请求信息
    request_payload: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="请求Payload"
    )
    response_status: Mapped[int | None] = mapped_column(
        Integer, comment="HTTP状态码"
    )
    response_body: Mapped[str | None] = mapped_column(
        Text, comment="响应内容"
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="状态(success/failed/pending)"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="重试次数"
    )

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(
        Text, comment="错误信息"
    )

    # 时间信息
    processed_at: Mapped[datetime | None] = mapped_column(
        comment="处理完成时间"
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer, comment="处理耗时（毫秒）"
    )

    # 关联关系
    config: Mapped["WebhookConfig"] = relationship(
        "WebhookConfig", back_populates="logs"
    )

    def __repr__(self) -> str:
        return f"<WebhookLog {self.event_type}>"
