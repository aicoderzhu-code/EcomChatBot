"""商品管理 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.product import (
    ProductListQuery, ProductResponse,
    SyncScheduleResponse, SyncScheduleUpdate,
    SyncTaskResponse, TriggerSyncRequest,
)
from services.product_sync_service import ProductSyncService
from tasks.product_sync_tasks import run_product_sync

router = APIRouter(prefix="/products", tags=["商品管理"])


# ===== 同步相关（固定路由必须在参数路由之前） =====

@router.post("/sync", response_model=ApiResponse[SyncTaskResponse])
async def trigger_sync(
    request: TriggerSyncRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """触发商品同步"""
    service = ProductSyncService(db, tenant_id)
    try:
        task = await service.trigger_sync(
            platform_config_id=request.platform_config_id,
            sync_type=request.sync_type,
        )
    except ValueError as e:
        return ApiResponse(success=False, error={"code": "SYNC_CONFLICT", "message": str(e)})

    # 异步执行
    run_product_sync.delay(task.id, tenant_id)

    return ApiResponse(data=task)


@router.get("/sync/tasks", response_model=ApiResponse[PaginatedResponse[SyncTaskResponse]])
async def list_sync_tasks(
    tenant_id: TenantFlexDep,
    db: DBDep,
    platform_config_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询同步任务列表"""
    service = ProductSyncService(db, tenant_id)
    tasks, total = await service.list_sync_tasks(
        platform_config_id=platform_config_id,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(
        items=tasks, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


# ===== 同步调度 =====

@router.get("/sync/schedule/{platform_config_id}", response_model=ApiResponse[SyncScheduleResponse | None])
async def get_sync_schedule(
    platform_config_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取同步调度配置"""
    service = ProductSyncService(db, tenant_id)
    schedule = await service.get_sync_schedule(platform_config_id)
    return ApiResponse(data=schedule)


@router.put("/sync/schedule/{platform_config_id}", response_model=ApiResponse[SyncScheduleResponse])
async def update_sync_schedule(
    platform_config_id: int,
    request: SyncScheduleUpdate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新同步调度配置"""
    service = ProductSyncService(db, tenant_id)
    schedule = await service.update_sync_schedule(
        platform_config_id=platform_config_id,
        interval_minutes=request.interval_minutes,
        is_active=request.is_active,
    )
    return ApiResponse(data=schedule)


# ===== 商品 CRUD =====

@router.get("", response_model=ApiResponse[PaginatedResponse[ProductResponse]])
async def list_products(
    tenant_id: TenantFlexDep,
    db: DBDep,
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    platform_config_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询商品列表"""
    service = ProductSyncService(db, tenant_id)
    products, total = await service.list_products(
        keyword=keyword,
        category=category,
        status=status,
        platform_config_id=platform_config_id,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(
        items=products, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.get("/{product_id}", response_model=ApiResponse[ProductResponse])
async def get_product(
    product_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取商品详情"""
    service = ProductSyncService(db, tenant_id)
    product = await service.get_product(product_id)
    if not product:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "商品不存在"})
    return ApiResponse(data=product)
