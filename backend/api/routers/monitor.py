"""
监控相关API路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantDep
from schemas.base import ApiResponse
from schemas.monitor import (
    ConversationStatsResponse,
    ResponseTimeStatsResponse,
    SatisfactionStatsResponse,
    DashboardSummaryResponse,
    HourlyTrendResponse
)
from services.monitor_service import MonitorService


router = APIRouter(prefix="/monitor", tags=["监控"])


@router.get("/conversations", response_model=ApiResponse[ConversationStatsResponse])
async def get_conversation_stats(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    获取对话统计

    - **start_time**: 开始时间（默认24小时前）
    - **end_time**: 结束时间（默认当前时间）
    """
    service = MonitorService(db, tenant_id)
    stats = await service.get_conversation_stats(start_time, end_time)

    return ApiResponse(data=ConversationStatsResponse(**stats))


@router.get("/response-time", response_model=ApiResponse[ResponseTimeStatsResponse])
async def get_response_time_stats(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    获取响应时间统计

    - **start_time**: 开始时间（默认24小时前）
    - **end_time**: 结束时间（默认当前时间）
    """
    service = MonitorService(db, tenant_id)
    stats = await service.get_response_time_stats(start_time, end_time)

    return ApiResponse(data=ResponseTimeStatsResponse(**stats))


@router.get("/satisfaction", response_model=ApiResponse[SatisfactionStatsResponse])
async def get_satisfaction_stats(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    获取满意度统计

    - **start_time**: 开始时间（默认24小时前）
    - **end_time**: 结束时间（默认当前时间）
    """
    service = MonitorService(db, tenant_id)
    stats = await service.get_satisfaction_stats(start_time, end_time)

    return ApiResponse(data=SatisfactionStatsResponse(**stats))


@router.get("/dashboard", response_model=ApiResponse[DashboardSummaryResponse])
async def get_dashboard_summary(
    time_range: str = Query("24h", description="时间范围: 24h, 7d, 30d"),
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    获取Dashboard汇总数据

    - **time_range**: 时间范围 (24h/7d/30d)
    """
    service = MonitorService(db, tenant_id)
    summary = await service.get_dashboard_summary(time_range)

    return ApiResponse(data=DashboardSummaryResponse(**summary))


@router.get("/trend/hourly", response_model=ApiResponse[list[HourlyTrendResponse]])
async def get_hourly_trend(
    hours: int = Query(24, ge=1, le=168, description="统计最近多少小时（最多7天）"),
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    获取每小时对话趋势

    - **hours**: 统计最近多少小时
    """
    service = MonitorService(db, tenant_id)
    trend = await service.get_hourly_conversation_trend(hours)

    return ApiResponse(data=[HourlyTrendResponse(**item) for item in trend])
