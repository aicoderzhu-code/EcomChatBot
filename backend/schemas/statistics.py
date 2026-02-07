"""
平台统计相关的Schema定义
"""
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

from schemas.base import BaseSchema


# ==================== 租户统计 ====================
class TenantStatistics(BaseModel):
    """租户统计"""

    total: int = Field(..., description="总租户数")
    active: int = Field(..., description="活跃租户数（本月有对话）")
    trial: int = Field(..., description="试用租户数")
    paid: int = Field(..., description="付费租户数")
    new_this_month: int = Field(..., description="本月新增")
    churned_this_month: int = Field(..., description="本月流失")
    churn_rate: float = Field(..., description="流失率(%)")


# ==================== 收入统计 ====================
class RevenueStatistics(BaseModel):
    """收入统计"""

    this_month: float = Field(..., description="本月收入")
    last_month: float = Field(..., description="上月收入")
    growth_rate: float = Field(..., description="增长率(%)")
    mrr: float = Field(..., description="月经常性收入(MRR)")
    arr: float = Field(..., description="年经常性收入(ARR)")
    pending_amount: float = Field(..., description="待收款金额")


# ==================== 用量统计 ====================
class UsageStatistics(BaseModel):
    """用量统计"""

    today_conversations: int = Field(..., description="今日对话数")
    month_conversations: int = Field(..., description="本月对话数")
    today_messages: int = Field(..., description="今日消息数")
    avg_response_time_ms: float = Field(..., description="平均响应时间(毫秒)")
    active_sessions: int = Field(..., description="当前在线会话数")


# ==================== 平台统计概览 ====================
class PlatformStatistics(BaseModel):
    """平台统计概览"""

    tenant_stats: TenantStatistics = Field(..., description="租户统计")
    revenue_stats: RevenueStatistics = Field(..., description="收入统计")
    usage_stats: UsageStatistics = Field(..., description="用量统计")
    plan_distribution: Dict[str, int] = Field(..., description="套餐分布")
    generated_at: datetime = Field(..., description="生成时间")


# ==================== 趋势数据 ====================
class DailyDataPoint(BaseModel):
    """每日数据点"""

    date: str = Field(..., description="日期(YYYY-MM-DD)")
    count: int | None = Field(None, description="数量")
    amount: float | None = Field(None, description="金额")


class TrendStatistics(BaseModel):
    """趋势统计"""

    period: str = Field(..., description="统计周期(7d/30d/90d)")
    new_tenants: List[DailyDataPoint] = Field(default_factory=list, description="每日新增租户")
    daily_revenue: List[DailyDataPoint] = Field(default_factory=list, description="每日收入")
    daily_conversations: List[DailyDataPoint] = Field(
        default_factory=list, description="每日对话数"
    )
