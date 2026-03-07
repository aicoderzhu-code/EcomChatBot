"""增购推荐 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.recommendation import (
    RecommendationLogResponse,
    RecommendationPreviewRequest,
    RecommendationRuleCreateRequest,
    RecommendationRuleResponse,
    RecommendationRuleUpdateRequest,
    RecommendationStatsResponse,
)
from services.recommendation_service import RecommendationService
from services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/recommendations", tags=["增购推荐"])


@router.post("/preview", response_model=ApiResponse)
async def preview_recommendations(
    request: RecommendationPreviewRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """预览推荐效果"""
    engine = RecommendationEngine(db, tenant_id)
    if request.product_id:
        result = await engine.get_in_conversation_recommendations(
            user_id=request.user_id or 0,
            current_product_id=request.product_id,
        )
    else:
        result = None
    return ApiResponse(data=result)


@router.post("/rules", response_model=ApiResponse[RecommendationRuleResponse])
async def create_rule(
    request: RecommendationRuleCreateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建推荐规则"""
    service = RecommendationService(db, tenant_id)
    rule = await service.create_rule(**request.model_dump())
    return ApiResponse(data=RecommendationRuleResponse.model_validate(rule))


@router.get("/rules", response_model=ApiResponse[PaginatedResponse[RecommendationRuleResponse]])
async def list_rules(
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """推荐规则列表"""
    service = RecommendationService(db, tenant_id)
    rules, total = await service.list_rules(page=page, size=size)
    items = [RecommendationRuleResponse.model_validate(r) for r in rules]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/rules/{rule_id}", response_model=ApiResponse[RecommendationRuleResponse])
async def get_rule(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """推荐规则详情"""
    service = RecommendationService(db, tenant_id)
    rule = await service.get_rule(rule_id)
    return ApiResponse(data=RecommendationRuleResponse.model_validate(rule))


@router.put("/rules/{rule_id}", response_model=ApiResponse[RecommendationRuleResponse])
async def update_rule(
    rule_id: int,
    request: RecommendationRuleUpdateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新推荐规则"""
    service = RecommendationService(db, tenant_id)
    rule = await service.update_rule(rule_id, **request.model_dump(exclude_unset=True))
    return ApiResponse(data=RecommendationRuleResponse.model_validate(rule))


@router.delete("/rules/{rule_id}", response_model=ApiResponse)
async def delete_rule(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除推荐规则"""
    service = RecommendationService(db, tenant_id)
    await service.delete_rule(rule_id)
    return ApiResponse(data={"message": "删除成功"})


@router.get("/logs", response_model=ApiResponse[PaginatedResponse[RecommendationLogResponse]])
async def list_logs(
    tenant_id: TenantFlexDep,
    db: DBDep,
    user_id: int | None = None,
    order_id: int | None = None,
    conversation_id: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """推荐记录"""
    service = RecommendationService(db, tenant_id)
    logs, total = await service.list_logs(
        user_id=user_id, order_id=order_id, conversation_id=conversation_id,
        page=page, size=size,
    )
    items = [RecommendationLogResponse.model_validate(l) for l in logs]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/stats", response_model=ApiResponse[RecommendationStatsResponse])
async def get_stats(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """推荐效果统计"""
    service = RecommendationService(db, tenant_id)
    stats = await service.get_stats()
    return ApiResponse(data=stats)
