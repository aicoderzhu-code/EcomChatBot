"""
质量评估相关API路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse
from schemas.quality import (
    ConversationQualityResponse,
    QualitySummaryResponse
)
from services.quality_service import QualityService


router = APIRouter(prefix="/quality", tags=["质量评估"])


@router.get("/conversation/{conversation_id}", response_model=ApiResponse[ConversationQualityResponse])
async def evaluate_conversation(
    conversation_id: str,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """
    评估单个对话的质量

    - **conversation_id**: 对话ID
    """
    service = QualityService(db, tenant_id)
    evaluation = await service.evaluate_conversation_quality(conversation_id)

    return ApiResponse(data=ConversationQualityResponse(**evaluation))


@router.get("/summary", response_model=ApiResponse[QualitySummaryResponse])
async def get_quality_summary(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """
    获取质量统计汇总

    - **start_time**: 开始时间（默认7天前）
    - **end_time**: 结束时间（默认当前时间）
    """
    service = QualityService(db, tenant_id)
    summary = await service.get_quality_summary(start_time, end_time)

    return ApiResponse(data=QualitySummaryResponse(**summary))
