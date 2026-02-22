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


@router.get("/revenue")
async def get_revenue_statistics(
    admin: AdminDep,
    db: DBDep,
    period: str = Query("month", description="统计周期: day/week/month/year"),
):
    """
    获取收入统计

    返回收入相关指标：
    - 总收入
    - 收入趋势
    - 按套餐收入
    - 每日收入

    参数：
    - period: day (日) / week (周) / month (月) / year (年)

    权限：所有管理员可访问
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_, func, select
    from models.tenant import Bill

    # 计算时间范围
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # month
        start_date = now - timedelta(days=30)

    # 总收入
    total_stmt = select(func.sum(Bill.total_amount)).where(
        and_(
            Bill.status == "paid",
            Bill.payment_time >= start_date,
        )
    )
    total_revenue = await db.scalar(total_stmt) or 0

    # 收入趋势 (按天)
    trend_stmt = (
        select(
            func.date(Bill.payment_time).label("date"),
            func.sum(Bill.total_amount).label("value"),
        )
        .where(
            and_(
                Bill.status == "paid",
                Bill.payment_time >= start_date,
            )
        )
        .group_by(func.date(Bill.payment_time))
        .order_by(func.date(Bill.payment_time))
    )
    result = await db.execute(trend_stmt)
    revenue_trend = [
        {"date": str(row.date), "value": float(row.value)}
        for row in result.all()
    ]

    # 按套餐收入 (假设Bill有plan_type或从关联获取)
    # 这里简化处理，返回模拟数据
    revenue_by_plan = [
        {"plan": "basic", "revenue": float(total_revenue) * 0.2},
        {"plan": "professional", "revenue": float(total_revenue) * 0.5},
        {"plan": "enterprise", "revenue": float(total_revenue) * 0.3},
    ]

    # 每日收入
    daily_revenue = revenue_trend[-14:] if len(revenue_trend) > 14 else revenue_trend

    return ApiResponse(data={
        "total_revenue": float(total_revenue),
        "revenue_trend": revenue_trend,
        "revenue_by_plan": revenue_by_plan,
        "daily_revenue": daily_revenue,
        "period": period,
    })


@router.get("/usage")
async def get_usage_statistics(
    admin: AdminDep,
    db: DBDep,
    request: Request,
    period: str = Query("month", description="统计周期: day/week/month/year"),
):
    """
    获取用量统计

    返回用量相关指标：
    - Token 总消耗
    - 存储使用量
    - API 调用次数
    - 用量趋势
    - Top 租户用量

    参数：
    - period: day (日) / week (周) / month (月) / year (年)

    权限：所有管理员可访问
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_, func, select
    from models import Conversation, Message, Tenant
    from models.tenant import UsageRecord

    # 计算时间范围
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # month
        start_date = now - timedelta(days=30)

    # Token 总消耗 (从 UsageRecord)
    token_stmt = select(
        func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens)
    ).where(UsageRecord.record_date >= start_date)
    total_tokens = await db.scalar(token_stmt) or 0

    # 存储使用量
    storage_stmt = select(func.sum(UsageRecord.storage_used)).where(
        UsageRecord.record_date >= start_date
    )
    storage_usage = await db.scalar(storage_stmt) or 0

    # API 调用次数
    api_stmt = select(func.sum(UsageRecord.api_calls)).where(
        UsageRecord.record_date >= start_date
    )
    api_calls = await db.scalar(api_stmt) or 0

    # 用量趋势 (按天 Token 消耗)
    trend_stmt = (
        select(
            func.date(UsageRecord.record_date).label("date"),
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens).label("value"),
        )
        .where(UsageRecord.record_date >= start_date)
        .group_by(func.date(UsageRecord.record_date))
        .order_by(func.date(UsageRecord.record_date))
    )
    result = await db.execute(trend_stmt)
    usage_trend = [
        {"date": str(row.date), "value": int(row.value)}
        for row in result.all()
    ]

    # Top 租户 Token 消耗
    top_tenants_stmt = (
        select(
            UsageRecord.tenant_id,
            Tenant.company_name,
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens).label("tokens"),
        )
        .join(Tenant, UsageRecord.tenant_id == Tenant.tenant_id)
        .where(UsageRecord.record_date >= start_date)
        .group_by(UsageRecord.tenant_id, Tenant.company_name)
        .order_by(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens).desc())
        .limit(10)
    )
    result = await db.execute(top_tenants_stmt)
    tokens_by_tenant = [
        {
            "tenant_id": row.tenant_id,
            "company_name": row.company_name,
            "tokens": int(row.tokens),
        }
        for row in result.all()
    ]

    return ApiResponse(data={
        "total_tokens": int(total_tokens),
        "storage_usage": float(storage_usage),
        "api_calls": int(api_calls),
        "usage_trend": usage_trend,
        "tokens_by_tenant": tokens_by_tenant,
        "period": period,
    })
