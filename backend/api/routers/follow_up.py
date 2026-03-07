"""定时跟进 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.follow_up import (
    FollowUpCreateRequest,
    FollowUpDashboardResponse,
    FollowUpResponse,
    FollowUpUpdateRequest,
)
from services.follow_up_service import FollowUpService

router = APIRouter(prefix="/follow-up", tags=["定时跟进"])


@router.get("/dashboard", response_model=ApiResponse[FollowUpDashboardResponse])
async def get_dashboard(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """跟进概览面板"""
    service = FollowUpService(db, tenant_id)
    data = await service.get_dashboard()
    return ApiResponse(data=data)


@router.post("/plans", response_model=ApiResponse[FollowUpResponse])
async def create_plan(
    request: FollowUpCreateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建跟进计划"""
    service = FollowUpService(db, tenant_id)
    plan = await service.create_plan(**request.model_dump())
    return ApiResponse(data=FollowUpResponse.model_validate(plan))


@router.get("/plans", response_model=ApiResponse[PaginatedResponse[FollowUpResponse]])
async def list_plans(
    tenant_id: TenantFlexDep,
    db: DBDep,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """跟进计划列表"""
    service = FollowUpService(db, tenant_id)
    plans, total = await service.list_plans(status=status, page=page, size=size)
    items = [FollowUpResponse.model_validate(p) for p in plans]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/plans/{plan_id}", response_model=ApiResponse[FollowUpResponse])
async def get_plan(
    plan_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """跟进计划详情"""
    service = FollowUpService(db, tenant_id)
    plan = await service.get_plan(plan_id)
    return ApiResponse(data=FollowUpResponse.model_validate(plan))


@router.put("/plans/{plan_id}", response_model=ApiResponse[FollowUpResponse])
async def update_plan(
    plan_id: int,
    request: FollowUpUpdateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新跟进计划"""
    service = FollowUpService(db, tenant_id)
    plan = await service.update_plan(plan_id, **request.model_dump(exclude_unset=True))
    return ApiResponse(data=FollowUpResponse.model_validate(plan))


@router.post("/plans/{plan_id}/cancel", response_model=ApiResponse[FollowUpResponse])
async def cancel_plan(
    plan_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """取消跟进计划"""
    service = FollowUpService(db, tenant_id)
    plan = await service.cancel_plan(plan_id)
    return ApiResponse(data=FollowUpResponse.model_validate(plan))


@router.post("/plans/{plan_id}/execute", response_model=ApiResponse)
async def execute_plan(
    plan_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """手动执行一次跟进"""
    service = FollowUpService(db, tenant_id)
    success = await service.execute_follow_up(plan_id)
    return ApiResponse(data={"executed": success})
