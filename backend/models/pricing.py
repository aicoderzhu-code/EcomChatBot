"""智能定价模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class CompetitorProduct(TenantBaseModel):
    """竞品数据表"""

    __tablename__ = "competitor_products"
    __table_args__ = (
        Index("idx_competitor_tenant", "tenant_id"),
        Index("idx_competitor_product", "product_id"),
        {"comment": "竞品数据表"},
    )

    product_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="关联商品ID"
    )
    competitor_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="竞品名称"
    )
    competitor_platform: Mapped[str | None] = mapped_column(
        String(64), comment="竞品平台"
    )
    competitor_url: Mapped[str | None] = mapped_column(
        String(1024), comment="竞品链接"
    )
    competitor_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="竞品价格"
    )
    competitor_sales: Mapped[int] = mapped_column(
        Integer, default=0, comment="竞品销量"
    )
    last_checked_at: Mapped[str | None] = mapped_column(
        DateTime, comment="最近检查时间"
    )

    def __repr__(self) -> str:
        return f"<CompetitorProduct {self.competitor_name} ¥{self.competitor_price}>"


class PricingStrategy(str, PyEnum):
    """定价策略"""

    COMPETITIVE = "competitive"
    PREMIUM = "premium"
    PENETRATION = "penetration"
    DYNAMIC = "dynamic"


class PricingAnalysis(TenantBaseModel):
    """定价分析结果表"""

    __tablename__ = "pricing_analyses"
    __table_args__ = (
        Index("idx_pricing_tenant", "tenant_id"),
        Index("idx_pricing_product", "product_id"),
        {"comment": "定价分析结果表"},
    )

    product_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="商品ID"
    )
    current_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="当前价格"
    )
    suggested_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="建议价格"
    )
    min_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="建议最低价"
    )
    max_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="建议最高价"
    )
    strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="competitive", comment="定价策略"
    )
    competitor_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="参考竞品数"
    )
    competitor_avg_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="竞品均价"
    )
    analysis_summary: Mapped[str | None] = mapped_column(
        Text, comment="分析摘要(AI生成)"
    )
    analysis_data: Mapped[dict | None] = mapped_column(
        JSONField, comment="详细分析数据(JSON)"
    )

    def __repr__(self) -> str:
        return f"<PricingAnalysis product={self.product_id} suggested=¥{self.suggested_price}>"
