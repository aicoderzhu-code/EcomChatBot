"""
运营分析 API 路由
"""
from fastapi import APIRouter, Depends, Query

from api.dependencies import AdminDep, DBDep, TenantDep, require_admin_permission
from core import Permission
from schemas.analytics import (
    ChurnAnalysisResponse,
    CohortAnalysisResponse,
    DashboardData,
    GrowthAnalysisResponse,
    HighValueTenantsResponse,
    LTVAnalysisResponse,
)
from schemas.base import ApiResponse
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["运营分析"])


# ============ 租户端数据分析（API Key 认证） ============


@router.get("", response_model=ApiResponse[dict])
async def get_tenant_analytics(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    租户获取基础分析数据（对话数、消息数等）

    使用 X-API-Key 认证
    """
    from services.monitor_service import MonitorService

    service = MonitorService(db, tenant_id)
    summary = await service.get_dashboard_summary("24h")
    return ApiResponse(data=summary)


@router.get("/conversations", response_model=ApiResponse[dict])
async def get_tenant_conversation_analytics(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    租户获取对话分析数据

    使用 X-API-Key 认证
    """
    from services.monitor_service import MonitorService

    service = MonitorService(db, tenant_id)
    stats = await service.get_conversation_stats()
    return ApiResponse(data=stats)


# ============ 管理端运营分析（Admin 认证） ============


@router.get("/growth", response_model=ApiResponse[GrowthAnalysisResponse])
async def get_growth_analysis(
    admin: AdminDep,
    db: DBDep,
    months: int = Query(12, ge=1, le=24, description="统计月数"),
):
    """
    租户增长分析
    
    返回指定月数的增长趋势：
    - 月度新增租户
    - 月度流失租户
    - 净增长
    - 累计租户数
    - 增长率
    
    权限：所有管理员可访问
    """
    service = AnalyticsService(db)
    data = await service.get_growth_analysis(months)
    return ApiResponse(data=GrowthAnalysisResponse(**data))


@router.get("/churn", response_model=ApiResponse[ChurnAnalysisResponse])
async def get_churn_analysis(
    admin: AdminDep,
    db: DBDep,
    months: int = Query(6, ge=1, le=12, description="统计月数"),
):
    """
    流失分析
    
    返回：
    - 月度流失率
    - 平均流失率
    - 流失风险租户列表
    
    权限：所有管理员可访问
    """
    service = AnalyticsService(db)
    data = await service.get_churn_analysis(months)
    return ApiResponse(data=ChurnAnalysisResponse(**data))


@router.get("/ltv", response_model=ApiResponse[LTVAnalysisResponse])
async def get_ltv_analysis(
    admin: AdminDep,
    db: DBDep,
    tenant_id: str | None = Query(None, description="租户ID(可选)"),
):
    """
    LTV（客户生命周期价值）分析
    
    计算公式: LTV = 平均月收入 × 预期生命周期(24个月)
    
    权限：所有管理员可访问
    """
    service = AnalyticsService(db)
    data = await service.calculate_ltv(tenant_id)
    return ApiResponse(data=LTVAnalysisResponse(ltv_data=data))


@router.get("/high-value-tenants", response_model=ApiResponse[HighValueTenantsResponse])
async def get_high_value_tenants(
    admin: AdminDep,
    db: DBDep,
    top_n: int = Query(20, ge=1, le=100, description="返回前N个"),
):
    """
    高价值租户识别
    
    多维度评分:
    - 收入贡献 (40%)
    - 活跃度 (30%)
    - 增长潜力 (20%)
    - 客户忠诚度 (10%)
    
    权限：所有管理员可访问
    """
    service = AnalyticsService(db)
    data = await service.identify_high_value_tenants(top_n)
    return ApiResponse(data=HighValueTenantsResponse(tenants=data))


@router.get("/cohort", response_model=ApiResponse[CohortAnalysisResponse])
async def get_cohort_analysis(
    admin: AdminDep,
    db: DBDep,
    months: int = Query(6, ge=3, le=12, description="分析的队列数"),
):
    """
    队列分析（留存率）
    
    按注册月份分组，追踪每个队列在后续月份的留存情况
    
    权限：所有管理员可访问
    """
    service = AnalyticsService(db)
    data = await service.get_cohort_analysis(months)
    return ApiResponse(data=CohortAnalysisResponse(**data))


@router.get("/dashboard", response_model=ApiResponse[DashboardData])
async def get_dashboard_data(
    admin: AdminDep,
    db: DBDep,
):
    """
    运营Dashboard综合数据
    
    一次性返回所有Dashboard所需数据：
    - 增长分析(最近6个月)
    - 流失分析(最近6个月)
    - Top 10高价值租户
    
    权限：所有管理员可访问
    """
    from datetime import datetime
    
    service = AnalyticsService(db)
    
    # 并发获取数据
    growth_data = await service.get_growth_analysis(months=6)
    churn_data = await service.get_churn_analysis(months=6)
    top_tenants = await service.identify_high_value_tenants(top_n=10)
    
    dashboard = DashboardData(
        growth=GrowthAnalysisResponse(**growth_data),
        churn=ChurnAnalysisResponse(**churn_data),
        top_tenants=top_tenants,
        generated_at=datetime.utcnow().isoformat(),
    )
    
    return ApiResponse(data=dashboard)
