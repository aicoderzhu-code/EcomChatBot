"""
通知相关数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class InAppNotification(BaseModel):
    """站内通知表"""
    __tablename__ = "in_app_notifications"

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True, comment="租户ID"
    )

    # 通知内容
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="通知标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="通知内容"
    )

    # 通知类型和优先级
    notification_type: Mapped[str] = mapped_column(
        String(32), default="system", nullable=False, comment="通知类型(system/billing/subscription/alert)"
    )
    priority: Mapped[str] = mapped_column(
        String(16), default="normal", nullable=False, comment="优先级(low/normal/high/urgent)"
    )

    # 关联链接
    link: Mapped[Optional[str]] = mapped_column(
        String(512), comment="关联链接"
    )

    # 元数据
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, comment="元数据"
    )

    # 阅读状态
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, comment="是否已读"
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="阅读时间"
    )

    # 索引
    __table_args__ = (
        Index('idx_notification_tenant_read', 'tenant_id', 'is_read'),
        Index('idx_notification_created', 'created_at'),
        {'comment': '站内通知表'}
    )

    def __repr__(self):
        return f"<InAppNotification(id={self.id}, tenant_id={self.tenant_id}, title={self.title})>"


class NotificationPreference(BaseModel):
    """通知偏好设置表"""
    __tablename__ = "notification_preferences"

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, unique=True, comment="租户ID"
    )

    # 邮件通知偏好
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用邮件通知"
    )
    email_subscription_expiring: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="订阅到期邮件通知"
    )
    email_payment: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="支付相关邮件通知"
    )
    email_quota_warning: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="配额预警邮件通知"
    )

    # 短信通知偏好
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否启用短信通知"
    )
    sms_subscription_expiring: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="订阅到期短信通知"
    )
    sms_payment: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="支付相关短信通知"
    )
    sms_quota_warning: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="配额预警短信通知"
    )

    # 站内信通知偏好
    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用站内信通知"
    )

    # 索引
    __table_args__ = (
        {'comment': '通知偏好设置表'}
    )

    def __repr__(self):
        return f"<NotificationPreference(tenant_id={self.tenant_id})>"
