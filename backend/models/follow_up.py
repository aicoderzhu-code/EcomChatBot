"""定时跟进模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class FollowUpReason(str, PyEnum):
    CHURN_RISK = "churn_risk"
    HIGH_POTENTIAL = "high_potential"
    POST_PURCHASE = "post_purchase"
    REACTIVATION = "reactivation"


class FollowUpStatus(str, PyEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CONVERTED = "converted"


class FollowUpPlan(TenantBaseModel):
    """定时跟进计划表"""

    __tablename__ = "follow_up_plans"
    __table_args__ = (
        Index("idx_followup_status_next", "status", "next_follow_up_at"),
        Index("idx_followup_tenant", "tenant_id"),
        Index("idx_followup_user", "user_id"),
        {"comment": "定时跟进计划表"},
    )

    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="目标用户ID"
    )
    rule_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联规则ID"
    )
    reason: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="跟进原因"
    )
    ai_context: Mapped[dict | None] = mapped_column(
        JSONField, comment="AI上下文(用户画像摘要等)"
    )
    total_steps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="总步骤数"
    )
    current_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当前步骤"
    )
    next_follow_up_at: Mapped[str | None] = mapped_column(
        DateTime, comment="下次跟进时间"
    )
    interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="跟进间隔(天)"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", comment="状态"
    )
    user_responded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="用户是否已回复"
    )
    converted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否已转化"
    )
    converted_order_id: Mapped[int | None] = mapped_column(
        Integer, comment="转化订单ID"
    )

    def __repr__(self) -> str:
        return f"<FollowUpPlan user={self.user_id} step={self.current_step}/{self.total_steps} ({self.status})>"
