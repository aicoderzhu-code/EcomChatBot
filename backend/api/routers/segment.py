"""客户分群 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.customer_segment import (
    SegmentAddMembersRequest,
    SegmentCreateRequest,
    SegmentMemberResponse,
    SegmentPreviewRequest,
    SegmentPreviewResponse,
    SegmentResponse,
    SegmentUpdateRequest,
)
from services.customer_segment_service import CustomerSegmentService

router = APIRouter(prefix="/segments", tags=["客户分群"])


@router.post("/preview", response_model=ApiResponse[SegmentPreviewResponse])
async def preview_segment(
    request: SegmentPreviewRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """预览匹配人数"""
    service = CustomerSegmentService(db, tenant_id)
    result = await service.preview_segment(request.filter_rules)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[SegmentResponse])
async def create_segment(
    request: SegmentCreateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建分群"""
    service = CustomerSegmentService(db, tenant_id)
    segment = await service.create_segment(**request.model_dump())
    return ApiResponse(data=SegmentResponse.model_validate(segment))


@router.get("", response_model=ApiResponse[PaginatedResponse[SegmentResponse]])
async def list_segments(
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """分群列表"""
    service = CustomerSegmentService(db, tenant_id)
    segments, total = await service.list_segments(page=page, size=size)
    items = [SegmentResponse.model_validate(s) for s in segments]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/{segment_id}", response_model=ApiResponse[SegmentResponse])
async def get_segment(
    segment_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """分群详情"""
    service = CustomerSegmentService(db, tenant_id)
    segment = await service.get_segment_detail(segment_id)
    return ApiResponse(data=SegmentResponse.model_validate(segment))


@router.put("/{segment_id}", response_model=ApiResponse[SegmentResponse])
async def update_segment(
    segment_id: int,
    request: SegmentUpdateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新分群"""
    service = CustomerSegmentService(db, tenant_id)
    segment = await service.update_segment(segment_id, **request.model_dump(exclude_unset=True))
    return ApiResponse(data=SegmentResponse.model_validate(segment))


@router.delete("/{segment_id}", response_model=ApiResponse)
async def delete_segment(
    segment_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除分群"""
    service = CustomerSegmentService(db, tenant_id)
    await service.delete_segment(segment_id)
    return ApiResponse(data={"message": "删除成功"})


@router.post("/{segment_id}/refresh", response_model=ApiResponse[SegmentResponse])
async def refresh_segment(
    segment_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """刷新分群成员"""
    service = CustomerSegmentService(db, tenant_id)
    segment = await service.refresh_segment_members(segment_id)
    return ApiResponse(data=SegmentResponse.model_validate(segment))


@router.get("/{segment_id}/members", response_model=ApiResponse[PaginatedResponse[SegmentMemberResponse]])
async def get_segment_members(
    segment_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """分群成员列表"""
    service = CustomerSegmentService(db, tenant_id)
    members, total = await service.get_segment_members(segment_id, page=page, size=size)
    return ApiResponse(data=PaginatedResponse.create(items=members, total=total, page=page, size=size))


@router.post("/{segment_id}/members", response_model=ApiResponse)
async def add_segment_members(
    segment_id: int,
    request: SegmentAddMembersRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """手动添加成员"""
    service = CustomerSegmentService(db, tenant_id)
    added = await service.add_members(segment_id, request.user_ids)
    return ApiResponse(data={"added": added})
