"""客户分群模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel, BaseModel
from models.product import JSONField


class SegmentType(str, PyEnum):
    MANUAL = "manual"
    DYNAMIC = "dynamic"


class CustomerSegment(TenantBaseModel):
    """客户分群表"""

    __tablename__ = "customer_segments"
    __table_args__ = (
        Index("idx_segment_tenant", "tenant_id"),
        Index("idx_segment_type", "segment_type"),
        {"comment": "客户分群表"},
    )

    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="分群名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="分群描述"
    )
    segment_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", comment="分群类型(manual/dynamic)"
    )
    filter_rules: Mapped[dict | None] = mapped_column(
        JSONField, comment="动态分群筛选条件(JSON)"
    )
    member_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="成员数量"
    )
    last_refreshed_at: Mapped[str | None] = mapped_column(
        DateTime, comment="最后刷新时间"
    )
    is_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="是否启用"
    )

    def __repr__(self) -> str:
        return f"<CustomerSegment {self.name} ({self.segment_type})>"


class CustomerSegmentMember(BaseModel):
    """客户分群成员表"""

    __tablename__ = "customer_segment_members"
    __table_args__ = (
        Index("idx_segment_member_unique", "segment_id", "user_id", unique=True),
        {"comment": "客户分群成员表"},
    )

    segment_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分群ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="用户ID"
    )
    added_at: Mapped[str | None] = mapped_column(
        DateTime, comment="添加时间"
    )

    def __repr__(self) -> str:
        return f"<SegmentMember segment={self.segment_id} user={self.user_id}>"
