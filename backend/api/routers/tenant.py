"""
租户管理 API 路由（租户自用）
"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantDep
from schemas import (
    ApiResponse,
    PaginatedResponse,
    QuotaUsageResponse,
    SubscriptionResponse,
    TenantResponse,
    UsageRecordResponse,
)
from services import QuotaService, SubscriptionService, TenantService, UsageService

router = APIRouter(prefix="/tenant", tags=["租户管理"])


@router.get("/info", response_model=ApiResponse[TenantResponse])
async def get_tenant_info(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取租户信息"""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=tenant)


@router.get("/subscription", response_model=ApiResponse[SubscriptionResponse])
async def get_subscription(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取订阅信息"""
    service = SubscriptionService(db)
    subscription = await service.get_subscription(tenant_id)
    return ApiResponse(data=subscription)


@router.get("/usage", response_model=ApiResponse[dict])
async def get_usage(
    tenant_id: TenantDep,
    db: DBDep,
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
):
    """获取用量统计"""
    service = UsageService(db)
    usage = await service.get_usage_summary(tenant_id, year, month)
    return ApiResponse(data=usage)


@router.get("/quota", response_model=ApiResponse[QuotaUsageResponse])
async def get_quota_usage(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取配额使用情况"""
    service = QuotaService(db)
    quota = await service.get_quota_usage(tenant_id)
    return ApiResponse(data=quota)
