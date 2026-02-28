"""订单数据模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class OrderStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Order(TenantBaseModel):
    """订单表"""

    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_order_tenant", "tenant_id"),
        Index("idx_order_platform", "platform_config_id"),
        Index("idx_order_status", "status"),
        Index("idx_order_product", "product_id"),
        {"comment": "订单表"},
    )

    platform_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="平台配置ID"
    )
    platform_order_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="平台订单号"
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联商品ID"
    )
    product_title: Mapped[str] = mapped_column(
        String(512), default="", comment="商品标题"
    )
    buyer_id: Mapped[str] = mapped_column(
        String(128), default="", comment="买家ID"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, default=1, comment="数量"
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0, comment="单价"
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0, comment="总金额"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", comment="状态"
    )
    paid_at: Mapped[str | None] = mapped_column(
        DateTime, comment="支付时间"
    )
    shipped_at: Mapped[str | None] = mapped_column(
        DateTime, comment="发货时间"
    )
    completed_at: Mapped[str | None] = mapped_column(
        DateTime, comment="完成时间"
    )
    refund_amount: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="退款金额"
    )
    platform_data: Mapped[dict | None] = mapped_column(
        JSONField, comment="平台原始数据(JSON)"
    )

    def __repr__(self) -> str:
        return f"<Order {self.platform_order_id} ({self.status})>"


class ReportType(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisReport(TenantBaseModel):
    """分析报告表"""

    __tablename__ = "analysis_reports"
    __table_args__ = (
        Index("idx_report_tenant", "tenant_id"),
        Index("idx_report_type", "report_type"),
        {"comment": "分析报告表"},
    )

    report_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="报告类型"
    )
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="报告标题"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", comment="状态"
    )
    period_start: Mapped[str | None] = mapped_column(
        DateTime, comment="分析起始时间"
    )
    period_end: Mapped[str | None] = mapped_column(
        DateTime, comment="分析结束时间"
    )
    summary: Mapped[str | None] = mapped_column(
        Text, comment="报告摘要(AI生成)"
    )
    statistics: Mapped[dict | None] = mapped_column(
        JSONField, comment="统计数据(JSON)"
    )
    charts_data: Mapped[dict | None] = mapped_column(
        JSONField, comment="图表数据(JSON)"
    )
    file_url: Mapped[str | None] = mapped_column(
        String(1024), comment="报告文件URL"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, comment="错误信息"
    )

    def __repr__(self) -> str:
        return f"<AnalysisReport {self.title} ({self.status})>"
