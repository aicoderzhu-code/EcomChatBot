"""售后记录模型"""
from sqlalchemy import Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class AfterSaleRecord(TenantBaseModel):
    """售后/退款记录表"""

    __tablename__ = "after_sale_records"
    __table_args__ = (
        Index("idx_aftersale_tenant_config", "tenant_id", "platform_config_id"),
        Index("idx_aftersale_platform_id", "platform_aftersale_id"),
        {"comment": "售后退款记录表"},
    )

    platform_config_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="关联平台配置ID")
    platform_aftersale_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="平台售后单号")
    order_id: Mapped[int | None] = mapped_column(Integer, comment="关联订单ID")

    aftersale_type: Mapped[str] = mapped_column(
        String(32), default="refund_only",
        comment="售后类型(refund_only/return_refund/exchange)"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending",
        comment="状态(pending/processing/approved/rejected/completed/cancelled)"
    )
    reason: Mapped[str | None] = mapped_column(Text, comment="售后原因")
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="退款金额")
    buyer_id: Mapped[str | None] = mapped_column(String(128), comment="买家ID")
    platform_data: Mapped[dict | None] = mapped_column(JSON, comment="平台原始数据")

    def __repr__(self) -> str:
        return f"<AfterSaleRecord {self.platform_aftersale_id} ({self.status})>"
