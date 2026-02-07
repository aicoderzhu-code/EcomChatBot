"""
平台统计 API 路由
"""
from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import AdminDep, DBDep, require_admin_permission
from core import Permission
from schemas.base import ApiResponse
from schemas.statistics import PlatformStatistics, TrendStatistics
from services.statistics_service import StatisticsService

router = APIRouter(prefix="/admin/statistics", tags=["平台统计"])


@router.get("/overview", response_model=ApiResponse[PlatformStatistics])
async def get_platform_statistics(
    admin: AdminDep,
    db: DBDep,
    request: Request,
):
    """
    获取平台统计概览

    返回关键运营指标：
    - 租户统计（总数、活跃、付费、试用、新增、流失）
    - 收入统计（本月、上月、MRR、ARR、待收款）
    - 用量统计（对话数、消息数、响应时间、在线会话）
    - 套餐分布

    权限：所有管理员可访问
    """
    service = StatisticsService(db)

    # 尝试获取Redis连接（用于实时指标）
    redis = getattr(request.app.state, "redis", None)

    overview = await service.get_overview(redis)

    return ApiResponse(data=PlatformStatistics(**overview))


@router.get("/trends", response_model=ApiResponse[TrendStatistics])
async def get_trend_statistics(
    admin: AdminDep,
    db: DBDep,
    period: str = Query("30d", regex="^(7d|30d|90d)$", description="统计周期"),
):
    """
    获取趋势统计数据

    返回指定周期内的每日数据：
    - 每日新增租户
    - 每日收入
    - 每日对话数

    参数：
    - period: 7d (7天) / 30d (30天) / 90d (90天)

    权限：所有管理员可访问
    """
    service = StatisticsService(db)

    trends = await service.get_trend_statistics(period)

    return ApiResponse(data=TrendStatistics(**trends))
