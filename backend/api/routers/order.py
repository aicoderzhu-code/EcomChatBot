"""订单管理 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.order import (
    OrderListQuery,
    OrderResponse,
    TriggerOrderSyncRequest,
)
from schemas.product import SyncTaskResponse
from services.order_sync_service import OrderSyncService
from services.order_analytics.analytics_service import OrderAnalyticsService

router = APIRouter(prefix="/orders", tags=["订单管理"])


# ===== 同步相关（固定路由在参数路由之前） =====


@router.post("/sync", response_model=ApiResponse[SyncTaskResponse])
async def trigger_order_sync(
    request: TriggerOrderSyncRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """触发订单同步"""
    service = OrderSyncService(db, tenant_id)
    try:
        task = await service.trigger_sync(
            platform_config_id=request.platform_config_id,
            start_time=request.start_time,
            end_time=request.end_time,
        )
    except ValueError as e:
        return ApiResponse(
            success=False,
            error={"code": "SYNC_CONFLICT", "message": str(e)},
        )
    return ApiResponse(data=task)


# ===== 分析相关 =====


@router.get("/analytics/overview", response_model=ApiResponse[dict])
async def get_order_overview(
    tenant_id: TenantFlexDep,
    db: DBDep,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
):
    """获取订单概览统计"""
    service = OrderAnalyticsService(db, tenant_id)
    overview = await service.get_overview(days=days)
    return ApiResponse(data=overview)


@router.get("/analytics/top-products", response_model=ApiResponse[list[dict]])
async def get_top_products(
    tenant_id: TenantFlexDep,
    db: DBDep,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """获取热销商品排行"""
    service = OrderAnalyticsService(db, tenant_id)
    products = await service.get_top_products(days=days, limit=limit)
    return ApiResponse(data=products)


@router.get("/analytics/buyer-stats", response_model=ApiResponse[list[dict]])
async def get_buyer_stats(
    tenant_id: TenantFlexDep,
    db: DBDep,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """获取买家统计"""
    service = OrderAnalyticsService(db, tenant_id)
    stats = await service.get_buyer_stats(days=days, limit=limit)
    return ApiResponse(data=stats)


# ===== 订单 CRUD =====


@router.get("", response_model=ApiResponse[PaginatedResponse[OrderResponse]])
async def list_orders(
    tenant_id: TenantFlexDep,
    db: DBDep,
    status: str | None = None,
    platform_config_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询订单列表"""
    service = OrderSyncService(db, tenant_id)
    orders, total = await service.list_orders(
        status=status,
        platform_config_id=platform_config_id,
        keyword=keyword,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(
        items=orders, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.get("/{order_id}", response_model=ApiResponse[OrderResponse])
async def get_order(
    order_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取订单详情"""
    service = OrderSyncService(db, tenant_id)
    order = await service.get_order(order_id)
    if not order:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "订单不存在"},
        )
    return ApiResponse(data=order)
