"""
自动知识提取 API 路由
"""
import logging

from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.knowledge_candidate import (
    ApproveRequest,
    BatchApproveRequest,
    KnowledgeCandidateResponse,
    RejectRequest,
)
from services.knowledge_extraction_service import KnowledgeExtractionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/candidates", tags=["自动知识提取"])


@router.get("", response_model=ApiResponse[PaginatedResponse[KnowledgeCandidateResponse]])
async def list_candidates(
    tenant_id: TenantFlexDep,
    db: DBDep,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询候选知识列表"""
    service = KnowledgeExtractionService(db, tenant_id)
    candidates, total = await service.list_candidates(
        status=status, page=page, size=size,
    )
    paginated = PaginatedResponse.create(
        items=candidates, total=total, page=page, size=size,
    )
    return ApiResponse(data=paginated)


@router.get("/metrics", response_model=ApiResponse[dict])
async def get_extraction_metrics(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取提取统计"""
    service = KnowledgeExtractionService(db, tenant_id)
    metrics = await service.get_metrics()
    return ApiResponse(data=metrics)


@router.post("/{candidate_id}/approve", response_model=ApiResponse[KnowledgeCandidateResponse])
async def approve_candidate(
    candidate_id: str,
    data: ApproveRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """审核通过候选知识"""
    service = KnowledgeExtractionService(db, tenant_id)
    candidate = await service.approve_candidate(
        candidate_id,
        question=data.question,
        answer=data.answer,
        category=data.category,
    )
    return ApiResponse(data=candidate)


@router.post("/{candidate_id}/reject", response_model=ApiResponse[KnowledgeCandidateResponse])
async def reject_candidate(
    candidate_id: str,
    data: RejectRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """拒绝候选知识"""
    service = KnowledgeExtractionService(db, tenant_id)
    candidate = await service.reject_candidate(candidate_id, data.reason)
    return ApiResponse(data=candidate)


@router.post("/batch-approve", response_model=ApiResponse[dict])
async def batch_approve(
    data: BatchApproveRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """批量审核通过"""
    service = KnowledgeExtractionService(db, tenant_id)
    results = await service.batch_approve(data.candidate_ids)
    return ApiResponse(data=results)


@router.post("/extract/{conversation_id}", response_model=ApiResponse[list[KnowledgeCandidateResponse]])
async def extract_from_conversation(
    conversation_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """手动触发从对话中提取知识"""
    service = KnowledgeExtractionService(db, tenant_id)
    candidates = await service.extract_from_conversation(conversation_id)
    return ApiResponse(data=candidates)
