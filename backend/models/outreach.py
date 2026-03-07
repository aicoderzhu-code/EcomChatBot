"""智能外呼模型 — 活动、规则、任务"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class CampaignType(str, PyEnum):
    MANUAL = "manual"
    AUTO_RULE = "auto_rule"
    FOLLOW_UP = "follow_up"
    POST_PURCHASE = "post_purchase"


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentStrategy(str, PyEnum):
    TEMPLATE = "template"
    AI_GENERATED = "ai_generated"


class OutreachTaskStatus(str, PyEnum):
    PENDING = "pending"
    GENERATING = "generating"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CONVERTED = "converted"


class RuleType(str, PyEnum):
    CART_ABANDONED = "cart_abandoned"
    NEW_USER_INACTIVE = "new_user_inactive"
    POST_PURCHASE = "post_purchase"
    CHURN_RISK = "churn_risk"
    FOLLOW_UP = "follow_up"


class OutreachCampaign(TenantBaseModel):
    """外呼活动表"""

    __tablename__ = "outreach_campaigns"
    __table_args__ = (
        Index("idx_campaign_tenant_status", "tenant_id", "status"),
        {"comment": "外呼活动表"},
    )

    name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="活动名称"
    )
    campaign_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", comment="活动类型"
    )
    segment_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联分群ID"
    )
    rule_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联规则ID"
    )
    content_strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="template", comment="内容策略"
    )
    content_template: Mapped[str | None] = mapped_column(
        Text, comment="消息模板"
    )
    ai_prompt: Mapped[str | None] = mapped_column(
        Text, comment="AI生成提示词"
    )
    channel: Mapped[str | None] = mapped_column(
        String(32), default="platform_message", comment="发送渠道"
    )
    platform_type: Mapped[str | None] = mapped_column(
        String(32), comment="平台类型"
    )
    platform_config_id: Mapped[int | None] = mapped_column(
        Integer, comment="平台配置ID"
    )
    scheduled_at: Mapped[str | None] = mapped_column(
        DateTime, comment="计划发送时间"
    )
    started_at: Mapped[str | None] = mapped_column(
        DateTime, comment="实际开始时间"
    )
    completed_at: Mapped[str | None] = mapped_column(
        DateTime, comment="完成时间"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", comment="状态"
    )
    total_targets: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="目标人数"
    )
    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已发送数"
    )
    delivered_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="送达数"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="失败数"
    )
    clicked_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="点击数"
    )
    converted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="转化数"
    )
    max_per_user_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="每人每天最大触达次数"
    )
    cooldown_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24, comment="冷却时间(小时)"
    )

    def __repr__(self) -> str:
        return f"<OutreachCampaign {self.name} ({self.status})>"


class OutreachRule(TenantBaseModel):
    """自动触发规则表"""

    __tablename__ = "outreach_rules"
    __table_args__ = (
        Index("idx_rule_tenant", "tenant_id"),
        Index("idx_rule_active", "is_active"),
        {"comment": "自动触发规则表"},
    )

    name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="规则名称"
    )
    rule_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="规则类型"
    )
    trigger_conditions: Mapped[dict | None] = mapped_column(
        JSONField, comment="触发条件(JSON)"
    )
    content_strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="template", comment="内容策略"
    )
    content_template: Mapped[str | None] = mapped_column(
        Text, comment="消息模板"
    )
    ai_prompt: Mapped[str | None] = mapped_column(
        Text, comment="AI生成提示词"
    )
    channel: Mapped[str | None] = mapped_column(
        String(32), default="platform_message", comment="发送渠道"
    )
    platform_type: Mapped[str | None] = mapped_column(
        String(32), comment="平台类型"
    )
    platform_config_id: Mapped[int | None] = mapped_column(
        Integer, comment="平台配置ID"
    )
    is_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="是否启用"
    )
    max_triggers_per_user: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="每用户最大触发次数"
    )
    cooldown_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=72, comment="冷却时间(小时)"
    )
    total_triggered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="总触发次数"
    )
    total_converted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="总转化次数"
    )

    def __repr__(self) -> str:
        return f"<OutreachRule {self.name} ({self.rule_type})>"


class OutreachTask(TenantBaseModel):
    """触达任务表"""

    __tablename__ = "outreach_tasks"
    __table_args__ = (
        Index("idx_task_status_scheduled", "status", "scheduled_at"),
        Index("idx_task_user", "user_id"),
        Index("idx_task_campaign", "campaign_id"),
        Index("idx_task_tenant", "tenant_id"),
        {"comment": "触达任务表"},
    )

    campaign_id: Mapped[int | None] = mapped_column(
        Integer, comment="活动ID"
    )
    rule_id: Mapped[int | None] = mapped_column(
        Integer, comment="规则ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="目标用户ID"
    )
    content: Mapped[str | None] = mapped_column(
        Text, comment="消息内容"
    )
    content_generated_at: Mapped[str | None] = mapped_column(
        DateTime, comment="内容生成时间"
    )
    related_product_ids: Mapped[list | None] = mapped_column(
        JSONField, comment="关联商品ID列表(JSON)"
    )
    related_order_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联订单ID"
    )
    platform_type: Mapped[str | None] = mapped_column(
        String(32), comment="平台类型"
    )
    platform_config_id: Mapped[int | None] = mapped_column(
        Integer, comment="平台配置ID"
    )
    platform_conversation_id: Mapped[str | None] = mapped_column(
        String(256), comment="平台会话ID"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", comment="状态"
    )
    scheduled_at: Mapped[str | None] = mapped_column(
        DateTime, comment="计划发送时间"
    )
    sent_at: Mapped[str | None] = mapped_column(
        DateTime, comment="发送时间"
    )
    delivered_at: Mapped[str | None] = mapped_column(
        DateTime, comment="送达时间"
    )
    converted_at: Mapped[str | None] = mapped_column(
        DateTime, comment="转化时间"
    )
    follow_up_plan_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联跟进计划ID"
    )
    follow_up_sequence: Mapped[int | None] = mapped_column(
        Integer, comment="跟进序号"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, comment="错误信息"
    )

    def __repr__(self) -> str:
        return f"<OutreachTask user={self.user_id} ({self.status})>"
