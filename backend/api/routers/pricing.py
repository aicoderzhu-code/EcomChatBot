"""智能定价 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.pricing import (
    AnalyzePricingRequest,
    CompetitorProductCreate,
    CompetitorProductResponse,
    PricingAnalysisResponse,
)
from services.pricing.competitor_service import CompetitorService
from services.pricing.pricing_service import PricingService

router = APIRouter(prefix="/pricing", tags=["智能定价"])


# ===== 竞品管理 =====


@router.post(
    "/competitors",
    response_model=ApiResponse[CompetitorProductResponse],
)
async def add_competitor(
    request: CompetitorProductCreate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """添加竞品数据"""
    service = CompetitorService(db, tenant_id)
    comp = await service.add_competitor(
        product_id=request.product_id,
        competitor_name=request.competitor_name,
        competitor_price=request.competitor_price,
        competitor_platform=request.competitor_platform,
        competitor_url=request.competitor_url,
        competitor_sales=request.competitor_sales,
    )
    return ApiResponse(data=comp)


@router.get(
    "/competitors/{product_id}",
    response_model=ApiResponse[PaginatedResponse[CompetitorProductResponse]],
)
async def list_competitors(
    product_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询商品的竞品列表"""
    service = CompetitorService(db, tenant_id)
    competitors, total = await service.list_competitors(
        product_id=product_id, page=page, size=size
    )
    paginated = PaginatedResponse.create(
        items=competitors, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.delete(
    "/competitors/{competitor_id}",
    response_model=ApiResponse,
)
async def delete_competitor(
    competitor_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除竞品数据"""
    service = CompetitorService(db, tenant_id)
    deleted = await service.delete_competitor(competitor_id)
    if not deleted:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "竞品数据不存在"},
        )
    return ApiResponse(data=None)


# ===== 定价分析 =====


@router.post(
    "/analyze",
    response_model=ApiResponse[PricingAnalysisResponse],
)
async def analyze_pricing(
    request: AnalyzePricingRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """执行定价分析"""
    service = PricingService(db, tenant_id)
    try:
        analysis = await service.analyze_pricing(
            product_id=request.product_id,
            strategy=request.strategy,
        )
        return ApiResponse(data=analysis)
    except ValueError as e:
        return ApiResponse(
            success=False,
            error={"code": "INVALID_REQUEST", "message": str(e)},
        )


@router.get(
    "/analysis/{product_id}",
    response_model=ApiResponse[PricingAnalysisResponse],
)
async def get_latest_analysis(
    product_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取商品最新定价分析"""
    service = PricingService(db, tenant_id)
    analysis = await service.get_latest_analysis(product_id)
    if not analysis:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "暂无分析结果"},
        )
    return ApiResponse(data=analysis)


@router.get(
    "/analysis/{product_id}/history",
    response_model=ApiResponse[PaginatedResponse[PricingAnalysisResponse]],
)
async def list_analysis_history(
    product_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    """查询商品定价分析历史"""
    service = PricingService(db, tenant_id)
    analyses, total = await service.list_analyses(
        product_id=product_id, page=page, size=size
    )
    paginated = PaginatedResponse.create(
        items=analyses, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)
