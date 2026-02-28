"""订单和分析报告 Pydantic Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import BaseSchema, TimestampSchema


# ===== Order Schemas =====

class OrderResponse(TimestampSchema):
    """订单响应"""
    id: int
    tenant_id: str
    platform_config_id: int
    platform_order_id: str
    product_id: int | None = None
    product_title: str = ""
    buyer_id: str = ""
    quantity: int = 1
    unit_price: float = 0
    total_amount: float = 0
    status: str
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    completed_at: datetime | None = None
    refund_amount: float | None = None
    platform_data: dict | None = None


class OrderListQuery(BaseModel):
    """订单列表查询参数"""
    status: str | None = Field(
        None,
        pattern="^(pending|paid|shipped|completed|refunded|cancelled)$",
        description="状态筛选",
    )
    platform_config_id: int | None = Field(None, description="平台筛选")
    keyword: str | None = Field(None, description="搜索关键词(订单号/商品标题)")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")


class TriggerOrderSyncRequest(BaseModel):
    """触发订单同步请求"""
    platform_config_id: int = Field(..., description="平台配置ID")
    start_time: datetime | None = Field(None, description="同步起始时间")
    end_time: datetime | None = Field(None, description="同步结束时间")


# ===== AnalysisReport Schemas =====

class AnalysisReportResponse(TimestampSchema):
    """分析报告响应"""
    id: int
    tenant_id: str
    report_type: str
    title: str
    status: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    summary: str | None = None
    statistics: dict | None = None
    charts_data: dict | None = None
    file_url: str | None = None
    error_message: str | None = None


class CreateReportRequest(BaseModel):
    """创建报告请求"""
    report_type: str = Field(
        ...,
        pattern="^(daily|weekly|monthly|custom)$",
        description="报告类型",
    )
    title: str = Field(..., min_length=1, max_length=256, description="报告标题")
    period_start: datetime | None = Field(None, description="分析起始时间")
    period_end: datetime | None = Field(None, description="分析结束时间")
