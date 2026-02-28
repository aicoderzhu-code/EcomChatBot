"""定价相关 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


class CompetitorProductCreate(BaseModel):
    """创建竞品数据"""

    product_id: int = Field(..., description="关联商品ID")
    competitor_name: str = Field(..., min_length=1, max_length=256)
    competitor_platform: str | None = None
    competitor_url: str | None = None
    competitor_price: float = Field(..., ge=0)
    competitor_sales: int = Field(0, ge=0)


class CompetitorProductResponse(TimestampSchema):
    """竞品数据响应"""

    id: int
    tenant_id: str
    product_id: int
    competitor_name: str
    competitor_platform: str | None = None
    competitor_url: str | None = None
    competitor_price: float
    competitor_sales: int
    last_checked_at: datetime | None = None


class PricingAnalysisResponse(TimestampSchema):
    """定价分析响应"""

    id: int
    tenant_id: str
    product_id: int
    current_price: float
    suggested_price: float
    min_price: float | None = None
    max_price: float | None = None
    strategy: str
    competitor_count: int
    competitor_avg_price: float | None = None
    analysis_summary: str | None = None
    analysis_data: dict | None = None


class AnalyzePricingRequest(BaseModel):
    """定价分析请求"""

    product_id: int = Field(..., description="商品ID")
    strategy: str = Field(
        "competitive",
        pattern="^(competitive|premium|penetration|dynamic)$",
    )
