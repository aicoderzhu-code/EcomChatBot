"""
运营分析相关的Schema定义
"""
from typing import Dict, List

from pydantic import BaseModel, Field

from schemas.base import BaseSchema


# ==================== 增长分析 ====================
class MonthlyGrowthData(BaseModel):
    """月度增长数据"""

    month: str = Field(..., description="月份(YYYY-MM)")
    new: int = Field(..., description="新增租户数")
    churned: int = Field(..., description="流失租户数")
    net: int = Field(..., description="净增租户数")
    cumulative: int = Field(..., description="累计租户数")
    growth_rate: float | None = Field(None, description="增长率(%)")


class GrowthAnalysisResponse(BaseModel):
    """增长分析响应"""

    monthly_data: List[MonthlyGrowthData] = Field(default_factory=list, description="月度数据")
    total_growth: int = Field(..., description="总增长数")
    avg_monthly_growth: float = Field(..., description="平均月增长数")


# ==================== 流失分析 ====================
class MonthlyChurnData(BaseModel):
    """月度流失数据"""

    month: str = Field(..., description="月份(YYYY-MM)")
    start_count: int = Field(..., description="月初租户数")
    churned: int = Field(..., description="流失数")
    churn_rate: float = Field(..., description="流失率(%)")


class AtRiskTenant(BaseModel):
    """流失风险租户"""

    tenant_id: str = Field(..., description="租户ID")
    company_name: str = Field(..., description="公司名称")
    plan: str = Field(..., description="套餐")
    expires_at: str = Field(..., description="到期时间")
    days_until_expiry: int = Field(..., description="距到期天数")
    recent_activity: int = Field(..., description="最近活跃度")
    risk_level: str = Field(..., description="风险等级(high/medium/low)")


class ChurnAnalysisResponse(BaseModel):
    """流失分析响应"""

    monthly_churn: List[MonthlyChurnData] = Field(default_factory=list, description="月度流失数据")
    avg_churn_rate: float = Field(..., description="平均流失率(%)")
    at_risk_tenants: List[AtRiskTenant] = Field(default_factory=list, description="风险租户列表")


# ==================== LTV分析 ====================
class LTVData(BaseModel):
    """LTV数据"""

    tenant_id: str = Field(..., description="租户ID")
    company_name: str = Field(..., description="公司名称")
    ltv: float = Field(..., description="生命周期价值")
    months_active: int = Field(..., description="活跃月数")
    total_revenue: float = Field(..., description="总收入")
    avg_monthly_revenue: float = Field(..., description="平均月收入")


class LTVAnalysisResponse(BaseModel):
    """LTV分析响应"""

    ltv_data: List[LTVData] = Field(default_factory=list, description="LTV数据列表")


# ==================== 高价值租户 ====================
class ValueScoreBreakdown(BaseModel):
    """价值分数明细"""

    revenue: float = Field(..., description="收入贡献分(0-40)")
    activity: float = Field(..., description="活跃度分(0-30)")
    growth: float = Field(..., description="增长潜力分(0-20)")
    loyalty: float = Field(..., description="忠诚度分(0-10)")


class HighValueTenant(BaseModel):
    """高价值租户"""

    tenant_id: str = Field(..., description="租户ID")
    company_name: str = Field(..., description="公司名称")
    plan: str = Field(..., description="套餐")
    value_score: float = Field(..., description="价值分数(0-100)")
    score_breakdown: ValueScoreBreakdown = Field(..., description="分数明细")
    insights: List[str] = Field(default_factory=list, description="洞察标签")


class HighValueTenantsResponse(BaseModel):
    """高价值租户响应"""

    tenants: List[HighValueTenant] = Field(default_factory=list, description="高价值租户列表")


# ==================== Dashboard数据 ====================
class DashboardData(BaseModel):
    """Dashboard综合数据"""

    growth: GrowthAnalysisResponse | None = None
    churn: ChurnAnalysisResponse | None = None
    top_tenants: List[HighValueTenant] = Field(default_factory=list)
    generated_at: str = Field(..., description="生成时间")


# ==================== 队列分析 ====================
class CohortData(BaseModel):
    """队列数据"""

    cohort_month: str = Field(..., description="队列月份(YYYY-MM)")
    total_tenants: int = Field(..., description="该月注册租户总数")
    retention_rates: Dict[str, float] = Field(..., description="留存率 {月份偏移: 留存率}")


class CohortAnalysisResponse(BaseModel):
    """队列分析响应"""

    cohorts: List[CohortData] = Field(default_factory=list, description="队列数据列表")

