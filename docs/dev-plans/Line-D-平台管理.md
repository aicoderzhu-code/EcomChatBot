# Line D: 平台管理开发计划

> 负责领域: 管理后台API、统计分析、运营Dashboard
> 核心技能: CRUD开发、数据统计、报表生成
> 总周期: Week 3-9

---

## 一、开发线概述

### 1.1 职责范围

Line D 负责平台管理能力，包括：
- 管理员管理
- 租户管理增强
- 平台统计数据
- 运营分析Dashboard

### 1.2 阶段规划

| 阶段 | 周期 | 主要任务 | 交付目标 |
|------|------|----------|----------|
| 第一阶段 | - | (无) | Line D从第二阶段开始 |
| 第二阶段 | Week 3-6 | 平台管理API | 管理员CRUD、批量操作、统计 |
| 第三阶段 | Week 7-9 | 运营分析 | 增长分析、流失预测、Dashboard |

### 1.3 依赖关系

```
Line D 输出 (被其他线依赖):
└── 统计API → 前端Dashboard使用

Line D 输入 (依赖其他线):
├── Line A: JWT认证、权限装饰器
├── Line B: 计费数据、配额数据
└── Line E: 监控指标数据
```

---

## 二、第二阶段：平台管理API (Week 3-6)

### 2.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| D2.1 | 管理员CRUD | P0 | 1.5天 | 待开始 |
| D2.2 | API密钥重置 | P1 | 0.5天 | 待开始 |
| D2.3 | 批量操作接口 | P0 | 1.5天 | 待开始 |
| D2.4 | 导出功能 | P1 | 1天 | 待开始 |
| D2.5 | 平台统计API | P0 | 2天 | 待开始 |
| D2.6 | 租户权限查看 | P1 | 0.5天 | 待开始 |
| D2.7 | 欠费租户列表 | P1 | 1天 | 待开始 |
| D2.8 | 账单审核 | P1 | 1天 | 待开始 |

### 2.2 详细设计

#### D2.1 管理员CRUD

**文件**: `backend/api/routers/admin.py` (扩展)

```python
from backend.api.middleware.permission import require_role, require_permissions, Role, Permission

# ==================== 管理员管理 ====================

@router.get("/admins", response_model=AdminListResponse)
@require_role(Role.SUPER_ADMIN)
async def list_admins(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str = Query(None),
    status: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取管理员列表

    权限: 仅超级管理员
    """
    query = db.query(Admin)

    # 过滤条件
    if role:
        query = query.filter(Admin.role == role)
    if status:
        query = query.filter(Admin.status == status)
    if search:
        query = query.filter(
            or_(
                Admin.username.ilike(f"%{search}%"),
                Admin.email.ilike(f"%{search}%"),
                Admin.name.ilike(f"%{search}%")
            )
        )

    # 分页
    total = query.count()
    admins = query.offset((page - 1) * page_size).limit(page_size).all()

    return AdminListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AdminInfo.from_orm(a) for a in admins]
    )

@router.post("/admins", response_model=AdminInfo)
@require_role(Role.SUPER_ADMIN)
async def create_admin(
    request: Request,
    body: CreateAdminRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    创建管理员

    权限: 仅超级管理员
    """
    # 检查用户名唯一
    existing = db.query(Admin).filter(Admin.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱唯一
    existing = db.query(Admin).filter(Admin.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 创建管理员
    admin = Admin(
        username=body.username,
        email=body.email,
        name=body.name,
        role=body.role,
        password_hash=hash_password(body.password),
        status="active"
    )
    db.add(admin)

    # 记录操作日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation="create_admin",
        target_type="admin",
        target_id=str(admin.id),
        details={"username": body.username, "role": body.role}
    )
    db.add(log)

    db.commit()
    db.refresh(admin)

    return AdminInfo.from_orm(admin)

@router.get("/admins/{admin_id}", response_model=AdminDetail)
@require_role(Role.SUPER_ADMIN)
async def get_admin(
    admin_id: str,
    db: Session = Depends(get_db)
):
    """获取管理员详情"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 获取最近操作日志
    recent_logs = db.query(AdminOperationLog).filter(
        AdminOperationLog.admin_id == admin_id
    ).order_by(AdminOperationLog.created_at.desc()).limit(10).all()

    return AdminDetail(
        **AdminInfo.from_orm(admin).dict(),
        recent_operations=[LogItem.from_orm(l) for l in recent_logs]
    )

@router.put("/admins/{admin_id}", response_model=AdminInfo)
@require_role(Role.SUPER_ADMIN)
async def update_admin(
    admin_id: str,
    body: UpdateAdminRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新管理员"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 不能修改自己的角色
    if str(admin.id) == str(current_admin.id) and body.role and body.role != admin.role:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    # 更新字段
    update_data = body.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(admin, key, value)

    # 记录操作日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation="update_admin",
        target_type="admin",
        target_id=admin_id,
        details=update_data
    )
    db.add(log)

    db.commit()
    db.refresh(admin)

    return AdminInfo.from_orm(admin)

@router.delete("/admins/{admin_id}")
@require_role(Role.SUPER_ADMIN)
async def delete_admin(
    admin_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除管理员(软删除)"""
    if str(admin_id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="不能删除自己")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    admin.status = "deleted"
    admin.deleted_at = datetime.utcnow()

    # 记录操作日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation="delete_admin",
        target_type="admin",
        target_id=admin_id,
        details={"username": admin.username}
    )
    db.add(log)

    db.commit()

    return {"message": "删除成功"}
```

---

#### D2.2 API密钥重置

```python
@router.post("/tenants/{tenant_id}/reset-api-key", response_model=ResetAPIKeyResponse)
@require_permissions(Permission.TENANT_WRITE)
async def reset_api_key(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    auth_service: AuthService = Depends()
):
    """
    重置租户API密钥

    - 生成新的API Key
    - 旧Key立即失效
    - 清除缓存
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 生成新API Key
    raw_key, hashed_key = auth_service.generate_api_key()

    # 更新数据库
    tenant.api_key_hash = hashed_key
    tenant.api_key_updated_at = datetime.utcnow()

    # 清除旧缓存
    redis = request.app.state.redis
    await redis.delete(f"api_key:{tenant.api_key_prefix}")

    # 更新前缀(用于缓存key)
    tenant.api_key_prefix = raw_key[:16]

    # 记录操作日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation="reset_api_key",
        target_type="tenant",
        target_id=tenant_id,
        details={"reason": "admin_reset"}
    )
    db.add(log)

    db.commit()

    # 发送通知给租户
    send_api_key_reset_notification.delay(tenant_id, raw_key)

    return ResetAPIKeyResponse(
        api_key=raw_key,  # 仅此次返回完整key
        message="API密钥已重置，请妥善保管新密钥"
    )
```

---

#### D2.3 批量操作接口

```python
class BatchOperationType(str, Enum):
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    DELETE = "delete"
    UPGRADE_PLAN = "upgrade_plan"
    DOWNGRADE_PLAN = "downgrade_plan"
    EXTEND_SERVICE = "extend_service"
    RESET_QUOTA = "reset_quota"

class BatchOperationRequest(BaseModel):
    tenant_ids: List[str] = Field(..., min_items=1, max_items=100)
    operation: BatchOperationType
    params: dict = Field(default_factory=dict)
    # params示例:
    # upgrade_plan: {"plan": "professional"}
    # extend_service: {"days": 30}

@router.post("/tenants/batch-operation", response_model=BatchOperationResponse)
@require_permissions(Permission.TENANT_WRITE)
async def batch_operation(
    body: BatchOperationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    批量操作租户

    支持:
    - 批量激活/暂停
    - 批量升级/降级套餐
    - 批量延期服务
    - 批量重置配额
    """
    results = []

    for tenant_id in body.tenant_ids:
        try:
            result = await _execute_batch_operation(
                db=db,
                tenant_id=tenant_id,
                operation=body.operation,
                params=body.params,
                admin_id=str(current_admin.id)
            )
            results.append({
                "tenant_id": tenant_id,
                "success": True,
                "message": result
            })
        except Exception as e:
            results.append({
                "tenant_id": tenant_id,
                "success": False,
                "error": str(e)
            })

    # 记录批量操作日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation=f"batch_{body.operation.value}",
        target_type="tenant",
        target_id=",".join(body.tenant_ids[:10]),  # 最多记录10个
        details={
            "operation": body.operation.value,
            "params": body.params,
            "total": len(body.tenant_ids),
            "success": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"])
        }
    )
    db.add(log)
    db.commit()

    return BatchOperationResponse(
        total=len(results),
        success=sum(1 for r in results if r["success"]),
        failed=sum(1 for r in results if not r["success"]),
        results=results
    )

async def _execute_batch_operation(
    db: Session,
    tenant_id: str,
    operation: BatchOperationType,
    params: dict,
    admin_id: str
) -> str:
    """执行单个批量操作"""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("租户不存在")

    if operation == BatchOperationType.ACTIVATE:
        tenant.status = "active"
        return "已激活"

    elif operation == BatchOperationType.SUSPEND:
        tenant.status = "suspended"
        return "已暂停"

    elif operation == BatchOperationType.DELETE:
        tenant.status = "deleted"
        tenant.deleted_at = datetime.utcnow()
        return "已删除"

    elif operation == BatchOperationType.UPGRADE_PLAN:
        new_plan = params.get("plan")
        if not new_plan:
            raise ValueError("缺少plan参数")
        subscription = tenant.subscription
        if subscription:
            subscription.plan = new_plan
            subscription.updated_at = datetime.utcnow()
        return f"已升级到{new_plan}"

    elif operation == BatchOperationType.EXTEND_SERVICE:
        days = params.get("days", 30)
        subscription = tenant.subscription
        if subscription:
            subscription.end_date += timedelta(days=days)
        return f"已延期{days}天"

    elif operation == BatchOperationType.RESET_QUOTA:
        # 重置Redis中的配额计数
        redis = get_redis()
        month = datetime.now().strftime("%Y%m")
        for quota_type in ["conversation", "api_call"]:
            key = f"quota:{tenant_id}:{quota_type}:{month}"
            await redis.delete(key)
        return "配额已重置"

    db.commit()
    return "操作成功"
```

---

#### D2.4 导出功能

```python
@router.get("/tenants/export")
@require_permissions(Permission.TENANT_READ)
async def export_tenants(
    request: Request,
    format: str = Query("csv", enum=["csv", "xlsx"]),
    status: str = Query(None),
    plan: str = Query(None),
    created_after: datetime = Query(None),
    created_before: datetime = Query(None),
    db: Session = Depends(get_db)
):
    """
    导出租户列表

    支持CSV和Excel格式
    """
    query = db.query(Tenant).filter(Tenant.status != "deleted")

    if status:
        query = query.filter(Tenant.status == status)
    if plan:
        query = query.join(Subscription).filter(Subscription.plan == plan)
    if created_after:
        query = query.filter(Tenant.created_at >= created_after)
    if created_before:
        query = query.filter(Tenant.created_at <= created_before)

    tenants = query.all()

    # 准备数据
    data = []
    for tenant in tenants:
        subscription = tenant.subscription
        data.append({
            "租户ID": str(tenant.id),
            "公司名称": tenant.company_name,
            "联系人": tenant.contact_name,
            "邮箱": tenant.email,
            "手机": tenant.phone,
            "状态": tenant.status,
            "套餐": subscription.plan if subscription else "无",
            "到期时间": subscription.end_date.strftime("%Y-%m-%d") if subscription else "",
            "创建时间": tenant.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    if format == "csv":
        return _generate_csv_response(data, "tenants_export.csv")
    else:
        return _generate_xlsx_response(data, "tenants_export.xlsx")

def _generate_csv_response(data: List[dict], filename: str):
    """生成CSV响应"""
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse

    output = StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def _generate_xlsx_response(data: List[dict], filename: str):
    """生成Excel响应"""
    from io import BytesIO
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse

    wb = Workbook()
    ws = wb.active
    ws.title = "租户列表"

    if data:
        # 写入表头
        headers = list(data[0].keys())
        ws.append(headers)

        # 写入数据
        for row in data:
            ws.append(list(row.values()))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

---

#### D2.5 平台统计API

```python
@router.get("/statistics/overview", response_model=PlatformStatistics)
@require_permissions(Permission.ADMIN_READ)
async def get_platform_statistics(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    平台统计概览

    返回关键运营指标
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # 租户统计
    tenant_stats = await _get_tenant_statistics(db, now, month_start)

    # 收入统计
    revenue_stats = await _get_revenue_statistics(db, month_start, last_month_start)

    # 用量统计
    usage_stats = await _get_usage_statistics(db, redis, today_start, month_start)

    # 套餐分布
    plan_distribution = await _get_plan_distribution(db)

    return PlatformStatistics(
        tenant_stats=tenant_stats,
        revenue_stats=revenue_stats,
        usage_stats=usage_stats,
        plan_distribution=plan_distribution,
        generated_at=now
    )

async def _get_tenant_statistics(db: Session, now: datetime, month_start: datetime) -> dict:
    """租户统计"""

    # 总租户数
    total = db.query(Tenant).filter(Tenant.status != "deleted").count()

    # 活跃租户(本月有对话)
    active = db.query(Tenant).join(Conversation).filter(
        Conversation.created_at >= month_start
    ).distinct().count()

    # 试用租户
    trial = db.query(Tenant).join(Subscription).filter(
        Subscription.plan == "free",
        Tenant.status == "active"
    ).count()

    # 付费租户
    paid = db.query(Tenant).join(Subscription).filter(
        Subscription.plan != "free",
        Subscription.status == "active"
    ).count()

    # 本月新增
    new_this_month = db.query(Tenant).filter(
        Tenant.created_at >= month_start,
        Tenant.status != "deleted"
    ).count()

    # 本月流失(从付费变为免费或注销)
    churned = db.query(Subscription).filter(
        Subscription.status == "expired",
        Subscription.end_date >= month_start
    ).count()

    return {
        "total": total,
        "active": active,
        "trial": trial,
        "paid": paid,
        "new_this_month": new_this_month,
        "churned_this_month": churned,
        "churn_rate": round(churned / paid * 100, 2) if paid > 0 else 0
    }

async def _get_revenue_statistics(
    db: Session,
    month_start: datetime,
    last_month_start: datetime
) -> dict:
    """收入统计"""

    # 本月收入
    this_month_revenue = db.query(func.sum(Bill.total_amount)).filter(
        Bill.status == "paid",
        Bill.paid_at >= month_start
    ).scalar() or 0

    # 上月收入
    last_month_revenue = db.query(func.sum(Bill.total_amount)).filter(
        Bill.status == "paid",
        Bill.paid_at >= last_month_start,
        Bill.paid_at < month_start
    ).scalar() or 0

    # MRR (月经常性收入)
    mrr = db.query(func.sum(
        case(
            (Subscription.billing_cycle == "monthly", Subscription.monthly_price),
            (Subscription.billing_cycle == "yearly", Subscription.monthly_price),
            else_=0
        )
    )).filter(
        Subscription.status == "active"
    ).scalar() or 0

    # ARR (年经常性收入)
    arr = mrr * 12

    # 待收款
    pending_amount = db.query(func.sum(Bill.total_amount)).filter(
        Bill.status == "pending"
    ).scalar() or 0

    return {
        "this_month": float(this_month_revenue),
        "last_month": float(last_month_revenue),
        "growth_rate": round((this_month_revenue - last_month_revenue) / last_month_revenue * 100, 2) if last_month_revenue > 0 else 0,
        "mrr": float(mrr),
        "arr": float(arr),
        "pending_amount": float(pending_amount)
    }

async def _get_usage_statistics(
    db: Session,
    redis,
    today_start: datetime,
    month_start: datetime
) -> dict:
    """用量统计"""

    # 今日对话数
    today_conversations = db.query(Conversation).filter(
        Conversation.created_at >= today_start
    ).count()

    # 本月对话数
    month_conversations = db.query(Conversation).filter(
        Conversation.created_at >= month_start
    ).count()

    # 今日消息数
    today_messages = db.query(Message).filter(
        Message.created_at >= today_start
    ).count()

    # 平均响应时间(从Redis获取)
    avg_response_time = await redis.get("metrics:avg_response_time:today")
    avg_response_time = float(avg_response_time) if avg_response_time else 0

    # 当前在线会话数
    active_sessions = await redis.scard("active_sessions")

    return {
        "today_conversations": today_conversations,
        "month_conversations": month_conversations,
        "today_messages": today_messages,
        "avg_response_time_ms": avg_response_time,
        "active_sessions": active_sessions
    }

async def _get_plan_distribution(db: Session) -> dict:
    """套餐分布"""

    distribution = db.query(
        Subscription.plan,
        func.count(Subscription.id)
    ).filter(
        Subscription.status == "active"
    ).group_by(Subscription.plan).all()

    return {plan: count for plan, count in distribution}

@router.get("/statistics/trends", response_model=TrendStatistics)
@require_permissions(Permission.ADMIN_READ)
async def get_trend_statistics(
    period: str = Query("30d", enum=["7d", "30d", "90d"]),
    db: Session = Depends(get_db)
):
    """
    趋势统计

    返回指定周期内的每日数据
    """
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    # 每日新增租户
    new_tenants = db.query(
        func.date(Tenant.created_at).label("date"),
        func.count(Tenant.id).label("count")
    ).filter(
        Tenant.created_at >= start_date
    ).group_by(func.date(Tenant.created_at)).all()

    # 每日收入
    daily_revenue = db.query(
        func.date(Bill.paid_at).label("date"),
        func.sum(Bill.total_amount).label("amount")
    ).filter(
        Bill.paid_at >= start_date,
        Bill.status == "paid"
    ).group_by(func.date(Bill.paid_at)).all()

    # 每日对话数
    daily_conversations = db.query(
        func.date(Conversation.created_at).label("date"),
        func.count(Conversation.id).label("count")
    ).filter(
        Conversation.created_at >= start_date
    ).group_by(func.date(Conversation.created_at)).all()

    return TrendStatistics(
        period=period,
        new_tenants=[{"date": str(r.date), "count": r.count} for r in new_tenants],
        daily_revenue=[{"date": str(r.date), "amount": float(r.amount)} for r in daily_revenue],
        daily_conversations=[{"date": str(r.date), "count": r.count} for r in daily_conversations]
    )
```

---

#### D2.7 欠费租户列表

```python
@router.get("/tenants/overdue", response_model=OverdueTenantListResponse)
@require_permissions(Permission.BILLING_READ)
async def get_overdue_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_days_overdue: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    获取欠费租户列表

    返回有未支付账单的租户
    """
    now = datetime.utcnow()

    # 查询有欠费的租户
    subquery = db.query(
        Bill.tenant_id,
        func.sum(Bill.total_amount).label("total_overdue"),
        func.min(Bill.due_date).label("oldest_due_date"),
        func.count(Bill.id).label("overdue_bills_count")
    ).filter(
        Bill.status == "pending",
        Bill.due_date < now
    ).group_by(Bill.tenant_id).subquery()

    query = db.query(
        Tenant,
        subquery.c.total_overdue,
        subquery.c.oldest_due_date,
        subquery.c.overdue_bills_count
    ).join(
        subquery, Tenant.id == subquery.c.tenant_id
    )

    # 按逾期天数过滤
    if min_days_overdue > 0:
        threshold_date = now - timedelta(days=min_days_overdue)
        query = query.filter(subquery.c.oldest_due_date <= threshold_date)

    # 按欠费金额排序
    query = query.order_by(subquery.c.total_overdue.desc())

    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for tenant, total_overdue, oldest_due_date, bills_count in results:
        days_overdue = (now - oldest_due_date).days
        items.append(OverdueTenantInfo(
            tenant_id=str(tenant.id),
            company_name=tenant.company_name,
            contact_name=tenant.contact_name,
            email=tenant.email,
            phone=tenant.phone,
            total_overdue=float(total_overdue),
            overdue_bills_count=bills_count,
            days_overdue=days_overdue,
            degradation_level=tenant.degradation_level
        ))

    return OverdueTenantListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )

@router.post("/tenants/{tenant_id}/send-reminder")
@require_permissions(Permission.BILLING_WRITE)
async def send_payment_reminder(
    tenant_id: str,
    body: SendReminderRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """发送催款提醒"""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取欠费信息
    overdue_bills = db.query(Bill).filter(
        Bill.tenant_id == tenant_id,
        Bill.status == "pending",
        Bill.due_date < datetime.utcnow()
    ).all()

    if not overdue_bills:
        raise HTTPException(status_code=400, detail="该租户无欠费账单")

    total_overdue = sum(b.total_amount for b in overdue_bills)

    # 发送提醒
    send_payment_reminder_notification.delay(
        tenant_id=tenant_id,
        total_overdue=float(total_overdue),
        bills_count=len(overdue_bills),
        message=body.custom_message
    )

    # 记录日志
    log = AdminOperationLog(
        admin_id=current_admin.id,
        operation="send_payment_reminder",
        target_type="tenant",
        target_id=tenant_id,
        details={"total_overdue": float(total_overdue)}
    )
    db.add(log)
    db.commit()

    return {"message": "催款提醒已发送"}
```

---

## 三、第三阶段：运营分析 (Week 7-9)

### 3.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| D3.1 | 租户增长分析 | P1 | 1.5天 | 待开始 |
| D3.2 | 流失率计算 | P1 | 1天 | 待开始 |
| D3.3 | LTV评估 | P2 | 1.5天 | 待开始 |
| D3.4 | 套餐分布分析 | P2 | 0.5天 | 待开始 |
| D3.5 | 高价值租户识别 | P2 | 1天 | 待开始 |
| D3.6 | 运营Dashboard API | P1 | 2天 | 待开始 |

### 3.2 详细设计

#### D3.1-D3.5 分析服务

**文件**: `backend/services/analytics_service.py` (新建)

```python
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta

@dataclass
class CohortData:
    """队列数据"""
    cohort_month: str
    total_tenants: int
    retention_rates: Dict[int, float]  # {month: rate}

@dataclass
class LTVData:
    """客户生命周期价值"""
    tenant_id: str
    ltv: float
    months_active: int
    total_revenue: float
    avg_monthly_revenue: float
    plan_history: List[str]

class AnalyticsService:
    """分析服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_growth_analysis(self, months: int = 12) -> dict:
        """
        租户增长分析

        返回:
        - 月度新增/流失/净增
        - 增长率
        - 累计租户数趋势
        """
        end_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=30 * months)

        monthly_data = []
        current_month = start_date

        while current_month < end_date:
            next_month = current_month + timedelta(days=32)
            next_month = next_month.replace(day=1)

            # 新增租户
            new_tenants = self.db.query(Tenant).filter(
                Tenant.created_at >= current_month,
                Tenant.created_at < next_month
            ).count()

            # 流失租户(订阅过期且未续费)
            churned = self.db.query(Subscription).filter(
                Subscription.status == "expired",
                Subscription.end_date >= current_month,
                Subscription.end_date < next_month
            ).count()

            # 累计活跃
            cumulative = self.db.query(Tenant).filter(
                Tenant.created_at < next_month,
                Tenant.status == "active"
            ).count()

            monthly_data.append({
                "month": current_month.strftime("%Y-%m"),
                "new": new_tenants,
                "churned": churned,
                "net": new_tenants - churned,
                "cumulative": cumulative
            })

            current_month = next_month

        # 计算增长率
        for i in range(1, len(monthly_data)):
            prev = monthly_data[i-1]["cumulative"]
            curr = monthly_data[i]["cumulative"]
            monthly_data[i]["growth_rate"] = round((curr - prev) / prev * 100, 2) if prev > 0 else 0

        return {
            "monthly_data": monthly_data,
            "total_growth": monthly_data[-1]["cumulative"] - monthly_data[0]["cumulative"] if monthly_data else 0,
            "avg_monthly_growth": sum(d["net"] for d in monthly_data) / len(monthly_data) if monthly_data else 0
        }

    async def get_churn_analysis(self, months: int = 6) -> dict:
        """
        流失分析

        返回:
        - 月度流失率
        - 流失原因分布
        - 流失预警名单
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)

        # 月度流失率
        monthly_churn = []
        current_month = start_date.replace(day=1)

        while current_month < end_date:
            next_month = (current_month + timedelta(days=32)).replace(day=1)

            # 月初活跃付费租户
            start_paid = self.db.query(Subscription).filter(
                Subscription.status == "active",
                Subscription.plan != "free",
                Subscription.created_at < current_month
            ).count()

            # 本月流失
            churned = self.db.query(Subscription).filter(
                Subscription.status == "expired",
                Subscription.end_date >= current_month,
                Subscription.end_date < next_month
            ).count()

            churn_rate = round(churned / start_paid * 100, 2) if start_paid > 0 else 0

            monthly_churn.append({
                "month": current_month.strftime("%Y-%m"),
                "start_count": start_paid,
                "churned": churned,
                "churn_rate": churn_rate
            })

            current_month = next_month

        # 流失风险预警(30天内到期且活跃度低)
        warning_threshold = end_date + timedelta(days=30)
        at_risk = self.db.query(Tenant).join(Subscription).filter(
            Subscription.end_date <= warning_threshold,
            Subscription.end_date > end_date,
            Subscription.auto_renew == False
        ).all()

        at_risk_list = []
        for tenant in at_risk:
            # 计算活跃度(最近30天对话数)
            recent_conversations = self.db.query(Conversation).filter(
                Conversation.tenant_id == tenant.id,
                Conversation.created_at >= end_date - timedelta(days=30)
            ).count()

            at_risk_list.append({
                "tenant_id": str(tenant.id),
                "company_name": tenant.company_name,
                "plan": tenant.subscription.plan,
                "expires_at": tenant.subscription.end_date.isoformat(),
                "days_until_expiry": (tenant.subscription.end_date - end_date).days,
                "recent_activity": recent_conversations,
                "risk_level": "high" if recent_conversations < 10 else "medium"
            })

        return {
            "monthly_churn": monthly_churn,
            "avg_churn_rate": sum(d["churn_rate"] for d in monthly_churn) / len(monthly_churn) if monthly_churn else 0,
            "at_risk_tenants": sorted(at_risk_list, key=lambda x: x["days_until_expiry"])
        }

    async def calculate_ltv(self, tenant_id: str = None) -> List[LTVData]:
        """
        计算客户生命周期价值(LTV)

        LTV = 平均月收入 × 客户生命周期(月)
        """
        query = self.db.query(Tenant).filter(Tenant.status != "deleted")

        if tenant_id:
            query = query.filter(Tenant.id == tenant_id)

        tenants = query.all()
        ltv_data = []

        for tenant in tenants:
            # 计算总收入
            total_revenue = self.db.query(func.sum(Bill.total_amount)).filter(
                Bill.tenant_id == tenant.id,
                Bill.status == "paid"
            ).scalar() or 0

            # 计算活跃月数
            first_payment = self.db.query(func.min(Bill.paid_at)).filter(
                Bill.tenant_id == tenant.id,
                Bill.status == "paid"
            ).scalar()

            if first_payment:
                months_active = max(1, (datetime.utcnow() - first_payment).days // 30)
            else:
                months_active = max(1, (datetime.utcnow() - tenant.created_at).days // 30)

            avg_monthly = total_revenue / months_active if months_active > 0 else 0

            # 预测LTV (假设平均客户生命周期24个月)
            expected_lifetime = 24
            ltv = avg_monthly * expected_lifetime

            ltv_data.append(LTVData(
                tenant_id=str(tenant.id),
                ltv=round(ltv, 2),
                months_active=months_active,
                total_revenue=float(total_revenue),
                avg_monthly_revenue=round(avg_monthly, 2),
                plan_history=[]  # TODO: 从历史记录获取
            ))

        return sorted(ltv_data, key=lambda x: x.ltv, reverse=True)

    async def identify_high_value_tenants(self, top_n: int = 20) -> List[dict]:
        """
        识别高价值租户

        评分维度:
        - 收入贡献 (40%)
        - 活跃度 (30%)
        - 增长潜力 (20%)
        - 客户忠诚度 (10%)
        """
        tenants = self.db.query(Tenant).filter(
            Tenant.status == "active"
        ).all()

        scored_tenants = []

        for tenant in tenants:
            score = await self._calculate_value_score(tenant)
            scored_tenants.append({
                "tenant_id": str(tenant.id),
                "company_name": tenant.company_name,
                "plan": tenant.subscription.plan if tenant.subscription else "free",
                "value_score": score["total"],
                "score_breakdown": score["breakdown"],
                "insights": score["insights"]
            })

        # 按分数排序
        scored_tenants.sort(key=lambda x: x["value_score"], reverse=True)

        return scored_tenants[:top_n]

    async def _calculate_value_score(self, tenant: Tenant) -> dict:
        """计算租户价值分数"""
        now = datetime.utcnow()

        # 1. 收入贡献分数 (0-40)
        total_revenue = self.db.query(func.sum(Bill.total_amount)).filter(
            Bill.tenant_id == tenant.id,
            Bill.status == "paid"
        ).scalar() or 0

        revenue_score = min(40, total_revenue / 1000 * 4)  # 每1000元4分

        # 2. 活跃度分数 (0-30)
        monthly_conversations = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.created_at >= now - timedelta(days=30)
        ).count()

        activity_score = min(30, monthly_conversations / 100 * 30)  # 100次对话满分

        # 3. 增长潜力分数 (0-20)
        # 基于套餐升级空间和使用率
        plan_order = {"free": 0, "basic": 1, "professional": 2, "enterprise": 3}
        current_plan = tenant.subscription.plan if tenant.subscription else "free"
        upgrade_potential = (3 - plan_order.get(current_plan, 0)) * 5

        growth_score = min(20, upgrade_potential + 5)  # 基础5分

        # 4. 忠诚度分数 (0-10)
        months_as_customer = (now - tenant.created_at).days // 30
        loyalty_score = min(10, months_as_customer)  # 每月1分,最多10分

        total = revenue_score + activity_score + growth_score + loyalty_score

        insights = []
        if revenue_score >= 30:
            insights.append("高收入贡献客户")
        if activity_score >= 25:
            insights.append("高活跃度用户")
        if upgrade_potential >= 10:
            insights.append("有升级潜力")
        if loyalty_score >= 8:
            insights.append("忠诚老客户")

        return {
            "total": round(total, 2),
            "breakdown": {
                "revenue": round(revenue_score, 2),
                "activity": round(activity_score, 2),
                "growth": round(growth_score, 2),
                "loyalty": round(loyalty_score, 2)
            },
            "insights": insights
        }
```

---

#### D3.6 运营Dashboard API

**文件**: `backend/api/routers/analytics.py` (新建)

```python
from fastapi import APIRouter, Depends, Query
from backend.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/dashboard")
@require_permissions(Permission.ADMIN_READ)
async def get_dashboard_data(
    analytics: AnalyticsService = Depends()
):
    """
    获取Dashboard完整数据

    一次返回所有Dashboard所需数据
    """
    return {
        "overview": await analytics.get_overview(),
        "growth": await analytics.get_growth_analysis(months=6),
        "churn": await analytics.get_churn_analysis(months=6),
        "top_tenants": await analytics.identify_high_value_tenants(top_n=10),
        "plan_distribution": await analytics.get_plan_distribution(),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/growth")
@require_permissions(Permission.ADMIN_READ)
async def get_growth_analysis(
    months: int = Query(12, ge=1, le=24),
    analytics: AnalyticsService = Depends()
):
    """租户增长分析"""
    return await analytics.get_growth_analysis(months)

@router.get("/churn")
@require_permissions(Permission.ADMIN_READ)
async def get_churn_analysis(
    months: int = Query(6, ge=1, le=12),
    analytics: AnalyticsService = Depends()
):
    """流失分析"""
    return await analytics.get_churn_analysis(months)

@router.get("/ltv")
@require_permissions(Permission.ADMIN_READ)
async def get_ltv_analysis(
    tenant_id: str = Query(None),
    analytics: AnalyticsService = Depends()
):
    """LTV分析"""
    return await analytics.calculate_ltv(tenant_id)

@router.get("/high-value-tenants")
@require_permissions(Permission.ADMIN_READ)
async def get_high_value_tenants(
    top_n: int = Query(20, ge=1, le=100),
    analytics: AnalyticsService = Depends()
):
    """高价值租户"""
    return await analytics.identify_high_value_tenants(top_n)

@router.get("/cohort")
@require_permissions(Permission.ADMIN_READ)
async def get_cohort_analysis(
    months: int = Query(6, ge=3, le=12),
    analytics: AnalyticsService = Depends()
):
    """队列分析(留存率)"""
    return await analytics.get_cohort_analysis(months)
```

---

## 四、接口契约汇总

### 4.1 管理员管理

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/v1/admin/admins` | GET | super_admin | 管理员列表 |
| `/api/v1/admin/admins` | POST | super_admin | 创建管理员 |
| `/api/v1/admin/admins/{id}` | GET | super_admin | 管理员详情 |
| `/api/v1/admin/admins/{id}` | PUT | super_admin | 更新管理员 |
| `/api/v1/admin/admins/{id}` | DELETE | super_admin | 删除管理员 |

### 4.2 租户管理

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/v1/admin/tenants/{id}/reset-api-key` | POST | tenant:write | 重置API Key |
| `/api/v1/admin/tenants/batch-operation` | POST | tenant:write | 批量操作 |
| `/api/v1/admin/tenants/export` | GET | tenant:read | 导出租户 |
| `/api/v1/admin/tenants/overdue` | GET | billing:read | 欠费租户 |

### 4.3 统计分析

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/v1/admin/statistics/overview` | GET | admin:read | 统计概览 |
| `/api/v1/admin/statistics/trends` | GET | admin:read | 趋势数据 |
| `/api/v1/analytics/dashboard` | GET | admin:read | Dashboard |
| `/api/v1/analytics/growth` | GET | admin:read | 增长分析 |
| `/api/v1/analytics/churn` | GET | admin:read | 流失分析 |
| `/api/v1/analytics/ltv` | GET | admin:read | LTV分析 |

---

## 五、验收标准

### 5.1 第二阶段验收 (Week 6末)

- [ ] 管理员CRUD正常
- [ ] 批量操作正确执行
- [ ] 导出功能可用
- [ ] 统计数据准确

### 5.2 第三阶段验收 (Week 9末)

- [ ] 增长分析准确
- [ ] 流失预警有效
- [ ] LTV计算合理
- [ ] Dashboard响应 < 2s

---

**文档维护者**: Line D负责人
**创建日期**: 2026-02-05
**版本**: v1.0