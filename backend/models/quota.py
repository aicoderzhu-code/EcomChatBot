"""
租户配额表模型
"""
from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class TenantQuota(BaseModel):
    """租户月度配额表"""

    __tablename__ = "tenant_quotas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "billing_period", name="uq_tenant_quota_period"),
        Index("idx_quota_tenant", "tenant_id"),
        Index("idx_quota_period", "billing_period"),
        {"comment": "租户月度配额表"},
    )

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="租户ID"
    )
    billing_period: Mapped[str] = mapped_column(
        String(7), nullable=False, comment="账期(格式: 2026-03)"
    )

    # AI回复配额
    reply_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3000, comment="AI回复配额"
    )
    reply_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="AI回复已用次数"
    )

    # 图片生成配额
    image_gen_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="图片生成配额"
    )
    image_gen_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="图片生成已用次数"
    )

    # 视频生成配额
    video_gen_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, comment="视频生成配额"
    )
    video_gen_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="视频生成已用次数"
    )

    def __repr__(self) -> str:
        return f"<TenantQuota {self.tenant_id} {self.billing_period}>"
