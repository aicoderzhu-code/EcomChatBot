"""分析报告 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.order import AnalysisReportResponse, CreateReportRequest
from services.order_analytics.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["分析报告"])


@router.post("", response_model=ApiResponse[AnalysisReportResponse])
async def create_report(
    request: CreateReportRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建分析报告"""
    service = ReportService(db, tenant_id)
    report = await service.create_report(
        report_type=request.report_type,
        title=request.title,
        period_start=request.period_start,
        period_end=request.period_end,
    )
    return ApiResponse(data=report)


@router.post("/{report_id}/generate", response_model=ApiResponse[AnalysisReportResponse])
async def generate_report(
    report_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """生成报告内容"""
    service = ReportService(db, tenant_id)
    report = await service.get_report(report_id)
    if not report:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "报告不存在"},
        )
    await service.generate_report(report_id)
    # 重新获取已更新的报告
    report = await service.get_report(report_id)
    return ApiResponse(data=report)


@router.get("", response_model=ApiResponse[PaginatedResponse[AnalysisReportResponse]])
async def list_reports(
    tenant_id: TenantFlexDep,
    db: DBDep,
    report_type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询报告列表"""
    service = ReportService(db, tenant_id)
    reports, total = await service.list_reports(
        report_type=report_type,
        status=status,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(
        items=reports, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.get("/{report_id}", response_model=ApiResponse[AnalysisReportResponse])
async def get_report(
    report_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取报告详情"""
    service = ReportService(db, tenant_id)
    report = await service.get_report(report_id)
    if not report:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "报告不存在"},
        )
    return ApiResponse(data=report)


@router.delete("/{report_id}", response_model=ApiResponse)
async def delete_report(
    report_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除报告"""
    service = ReportService(db, tenant_id)
    deleted = await service.delete_report(report_id)
    if not deleted:
        return ApiResponse(
            success=False,
            error={"code": "NOT_FOUND", "message": "报告不存在"},
        )
    return ApiResponse(data=None)
