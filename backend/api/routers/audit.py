"""
审计日志 API
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import AdminDep, DBDep, require_admin_permission
from core import Permission
from models.audit_log import AuditLog, AuditEventType, AuditSeverity
from schemas import ApiResponse

router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get(
    "/logs",
    dependencies=[Depends(require_admin_permission(Permission.STATISTICS_READ))],
)
async def get_audit_logs(
    admin: AdminDep,
    db: DBDep,
    tenant_id: Optional[str] = Query(None, description="租户ID筛选"),
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    severity: Optional[str] = Query(None, description="严重程度筛选"),
    success: Optional[bool] = Query(None, description="是否成功"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    ip_address: Optional[str] = Query(None, description="IP地址筛选"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    查询审计日志

    管理员权限：需要 STATISTICS_READ 权限
    """
    # 构建查询条件
    conditions = []

    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)

    if event_type:
        conditions.append(AuditLog.event_type == event_type)

    if severity:
        conditions.append(AuditLog.severity == severity)

    if success is not None:
        conditions.append(AuditLog.success == ("true" if success else "false"))

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)

    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    if ip_address:
        conditions.append(AuditLog.ip_address == ip_address)

    # 查询总数
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询数据
    query = (
        select(AuditLog)
        .where(and_(*conditions)) if conditions else select(AuditLog)
    )
    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return ApiResponse(
        data={
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get(
    "/logs/{log_id}",
    dependencies=[Depends(require_admin_permission(Permission.STATISTICS_READ))],
)
async def get_audit_log_detail(
    log_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    查询审计日志详情

    管理员权限：需要 STATISTICS_READ 权限
    """
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        return ApiResponse(code=404, message="审计日志不存在")

    return ApiResponse(data=log.to_dict())


@router.get(
    "/statistics/events",
    dependencies=[Depends(require_admin_permission(Permission.STATISTICS_READ))],
)
async def get_event_statistics(
    admin: AdminDep,
    db: DBDep,
    tenant_id: Optional[str] = Query(None, description="租户ID筛选"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
):
    """
    事件统计

    返回指定时间范围内各类事件的数量
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # 构建查询条件
    conditions = [AuditLog.created_at >= start_date]
    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)

    # 按事件类型统计
    query = (
        select(
            AuditLog.event_type,
            func.count().label("count")
        )
        .where(and_(*conditions))
        .group_by(AuditLog.event_type)
        .order_by(func.count().desc())
    )

    result = await db.execute(query)
    event_stats = [
        {"event_type": row[0], "count": row[1]}
        for row in result.fetchall()
    ]

    # 按严重程度统计
    severity_query = (
        select(
            AuditLog.severity,
            func.count().label("count")
        )
        .where(and_(*conditions))
        .group_by(AuditLog.severity)
    )

    severity_result = await db.execute(severity_query)
    severity_stats = [
        {"severity": row[0], "count": row[1]}
        for row in severity_result.fetchall()
    ]

    # 按天统计
    daily_query = (
        select(
            func.date(AuditLog.created_at).label("date"),
            func.count().label("count")
        )
        .where(and_(*conditions))
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
    )

    daily_result = await db.execute(daily_query)
    daily_stats = [
        {"date": row[0].isoformat(), "count": row[1]}
        for row in daily_result.fetchall()
    ]

    return ApiResponse(
        data={
            "event_statistics": event_stats,
            "severity_statistics": severity_stats,
            "daily_statistics": daily_stats,
            "period_days": days,
            "start_date": start_date.isoformat(),
        }
    )


@router.get(
    "/statistics/security-alerts",
    dependencies=[Depends(require_admin_permission(Permission.STATISTICS_READ))],
)
async def get_security_alerts(
    admin: AdminDep,
    db: DBDep,
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
):
    """
    安全警报

    返回最近的安全相关事件（WARNING 及以上级别）
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(AuditLog)
        .where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.severity.in_([
                    AuditSeverity.WARNING,
                    AuditSeverity.ERROR,
                    AuditSeverity.CRITICAL,
                ])
            )
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    alerts = result.scalars().all()

    # 统计各类安全事件数量
    security_events = [
        AuditEventType.LOGIN_FAILED,
        AuditEventType.PERMISSION_DENIED,
        AuditEventType.SUSPICIOUS_ACTIVITY,
        AuditEventType.RATE_LIMIT_EXCEEDED,
        AuditEventType.XSS_ATTEMPT_BLOCKED,
        AuditEventType.SQL_INJECTION_ATTEMPT,
        AuditEventType.ACCOUNT_LOCKED,
    ]

    event_counts = {}
    for event_type in security_events:
        count_query = select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.event_type == event_type.value
            )
        )
        count_result = await db.execute(count_query)
        event_counts[event_type.value] = count_result.scalar()

    return ApiResponse(
        data={
            "alerts": [alert.to_dict() for alert in alerts],
            "event_counts": event_counts,
            "period_days": days,
            "total_alerts": len(alerts),
        }
    )


@router.get(
    "/statistics/top-ips",
    dependencies=[Depends(require_admin_permission(Permission.STATISTICS_READ))],
)
async def get_top_ips(
    admin: AdminDep,
    db: DBDep,
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
):
    """
    活跃 IP 统计

    返回最活跃的 IP 地址及其活动情况
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            AuditLog.ip_address,
            func.count().label("total_events"),
            func.count(
                func.nullif(AuditLog.success, "true")
            ).label("failed_events"),
        )
        .where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.ip_address.isnot(None)
            )
        )
        .group_by(AuditLog.ip_address)
        .order_by(func.count().desc())
        .limit(limit)
    )

    result = await db.execute(query)
    ip_stats = [
        {
            "ip_address": str(row[0]),
            "total_events": row[1],
            "failed_events": row[2],
            "failure_rate": round(row[2] / row[1] * 100, 2) if row[1] > 0 else 0,
        }
        for row in result.fetchall()
    ]

    return ApiResponse(
        data={
            "top_ips": ip_stats,
            "period_days": days,
        }
    )