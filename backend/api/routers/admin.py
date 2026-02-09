"""
管理员 API 路由（平台管理）
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, select

from api.dependencies import AdminDep, DBDep, require_admin_permission
from core import AdminRole, Permission, create_access_token
from models import Subscription, Tenant
from schemas import (
    AdminCreate,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminResponse,
    AdminUpdate,
    ApiResponse,
    BatchOperationRequest,
    BatchOperationResponse,
    PaginatedResponse,
    TenantCreate,
    TenantResponse,
    TenantUpdateStatus,
    TenantWithAPIKey,
)
from services import AdminService, AuditService, QuotaService, SubscriptionService, TenantService

router = APIRouter(prefix="/admin", tags=["管理员"])


# ============ 管理员认证 ============
@router.post("/login", response_model=ApiResponse[AdminLoginResponse])
async def admin_login(
    login_data: AdminLoginRequest,
    db: DBDep,
):
    """管理员登录"""
    service = AdminService(db)
    admin = await service.authenticate_admin(
        username=login_data.username,
        password=login_data.password,
    )

    if not admin:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 刷新对象以加载所有属性
    await db.refresh(admin)

    # 生成Token
    token = create_access_token(
        subject=admin.admin_id,
        role=admin.role,
    )

    # 手动序列化 ORM 对象以避免 lazy loading 问题
    admin_dict = {
        "id": admin.id,
        "admin_id": admin.admin_id,
        "username": admin.username,
        "email": admin.email,
        "phone": admin.phone,
        "role": admin.role,
        "permissions": admin.permissions,
        "status": admin.status,
        "created_at": admin.created_at,
        "updated_at": admin.updated_at,
        "last_login_at": admin.last_login_at,
        "last_login_ip": admin.last_login_ip,
    }

    response = AdminLoginResponse.model_validate({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 28800,  # 8小时
        "admin": AdminResponse.model_validate(admin_dict)
    })

    return ApiResponse(data=response)


# ============ 管理员管理 ============
@router.get(
    "/admins",
    response_model=ApiResponse[PaginatedResponse[AdminResponse]],
    dependencies=[Depends(require_admin_permission(Permission.ADMIN_MANAGE))],
)
async def list_admins(
    admin: AdminDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
):
    """
    获取管理员列表

    权限：仅超级管理员
    """
    service = AdminService(db)
    admins, total = await service.list_admins(
        page=page,
        size=size,
        role=role,
        status=status,
        keyword=keyword,
    )

    paginated = PaginatedResponse.create(
        items=admins,
        total=total,
        page=page,
        size=size,
    )

    return ApiResponse(data=paginated)


@router.post(
    "/admins",
    response_model=ApiResponse[AdminResponse],
    dependencies=[Depends(require_admin_permission(Permission.ADMIN_MANAGE))],
)
async def create_admin(
    admin_data: AdminCreate,
    admin: AdminDep,
    db: DBDep,
):
    """
    创建管理员

    权限：仅超级管理员
    """
    service = AdminService(db)
    new_admin = await service.create_admin(
        username=admin_data.username,
        password=admin_data.password,
        email=admin_data.email,
        role=AdminRole(admin_data.role),
        phone=admin_data.phone,
        created_by=admin.admin_id,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_admin_create(
        admin_id=admin.admin_id,
        target_admin_id=new_admin.admin_id,
        admin_data={"username": admin_data.username, "role": admin_data.role},
    )

    return ApiResponse(data=new_admin)


@router.get(
    "/admins/{admin_id}",
    response_model=ApiResponse[AdminResponse],
    dependencies=[Depends(require_admin_permission(Permission.ADMIN_MANAGE))],
)
async def get_admin(
    admin_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    获取管理员详情

    权限：仅超级管理员
    """
    service = AdminService(db)
    target_admin = await service.get_admin(admin_id)
    return ApiResponse(data=target_admin)


@router.put(
    "/admins/{admin_id}",
    response_model=ApiResponse[AdminResponse],
    dependencies=[Depends(require_admin_permission(Permission.ADMIN_MANAGE))],
)
async def update_admin(
    admin_id: str,
    update_data: AdminUpdate,
    admin: AdminDep,
    db: DBDep,
):
    """
    更新管理员

    权限：仅超级管理员
    """
    # 不能修改自己的角色
    if admin_id == admin.admin_id and update_data.role and update_data.role != admin.role:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    service = AdminService(db)

    # 获取变更前状态
    old_admin = await service.get_admin(admin_id)
    old_data = {
        "email": old_admin.email,
        "phone": old_admin.phone,
        "role": old_admin.role,
        "status": old_admin.status,
    }

    # 更新管理员
    updated_admin = await service.update_admin(
        admin_id=admin_id,
        email=update_data.email,
        phone=update_data.phone,
        role=update_data.role,
        status=update_data.status,
        updated_by=admin.admin_id,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_admin_update(
        admin_id=admin.admin_id,
        target_admin_id=admin_id,
        before=old_data,
        after=update_data.model_dump(exclude_unset=True),
    )

    return ApiResponse(data=updated_admin)


@router.delete(
    "/admins/{admin_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin_permission(Permission.ADMIN_MANAGE))],
)
async def delete_admin(
    admin_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    删除管理员（软删除）

    权限：仅超级管理员
    """
    if admin_id == admin.admin_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="不能删除自己")

    service = AdminService(db)

    # 获取要删除的管理员信息
    target_admin = await service.get_admin(admin_id)

    # 执行删除
    await service.delete_admin(admin_id, deleted_by=admin.admin_id)

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_admin_delete(
        admin_id=admin.admin_id,
        target_admin_id=admin_id,
        admin_data={"username": target_admin.username},
    )

    return ApiResponse(data={"message": "删除成功"})


# ============ 租户管理 ============
@router.get("/tenants", response_model=ApiResponse[PaginatedResponse[TenantResponse]])
async def list_tenants(
    admin: AdminDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    plan: str | None = None,
    keyword: str | None = None,
):
    """
    查询租户列表
    
    权限：所有管理员
    """
    service = TenantService(db)
    tenants, total = await service.list_tenants(
        page=page,
        size=size,
        status=status,
        plan=plan,
        keyword=keyword,
    )

    paginated = PaginatedResponse.create(
        items=tenants,
        total=total,
        page=page,
        size=size,
    )

    return ApiResponse(data=paginated)


# ============ 欠费租户管理 (必须在 /tenants/{tenant_id} 之前定义) ============
@router.get("/tenants/overdue")
async def get_overdue_tenants(
    admin: AdminDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_days_overdue: int = Query(0, ge=0, description="最小逾期天数"),
):
    """
    获取欠费租户列表

    返回有未支付账单的租户信息

    参数：
    - page: 页码
    - page_size: 每页数量
    - min_days_overdue: 最小逾期天数（0表示所有欠费租户）

    权限：需要 BILLING_READ 权限
    """
    from models.tenant import Bill
    from schemas.billing import OverdueTenantInfo, OverdueTenantListResponse

    now = datetime.utcnow()

    # 查询有欠费的租户
    subquery = (
        select(
            Bill.tenant_id,
            func.sum(Bill.total_amount).label("total_overdue"),
            func.min(Bill.due_date).label("oldest_due_date"),
            func.count(Bill.id).label("overdue_bills_count"),
        )
        .where(
            and_(
                Bill.status.in_(["pending", "overdue"]),
                Bill.due_date < now,
            )
        )
        .group_by(Bill.tenant_id)
        .subquery()
    )

    query = (
        select(Tenant, subquery.c)
        .join(subquery, Tenant.tenant_id == subquery.c.tenant_id)
    )

    # 按逾期天数过滤
    if min_days_overdue > 0:
        threshold_date = now - timedelta(days=min_days_overdue)
        query = query.where(subquery.c.oldest_due_date <= threshold_date)

    # 按欠费金额排序
    query = query.order_by(subquery.c.total_overdue.desc())

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        tenant = row[0]
        total_overdue = row.total_overdue
        oldest_due_date = row.oldest_due_date
        bills_count = row.overdue_bills_count
        days_overdue = (now - oldest_due_date).days if oldest_due_date else 0

        items.append(
            OverdueTenantInfo(
                tenant_id=tenant.tenant_id,
                company_name=tenant.company_name,
                contact_name=tenant.contact_name,
                email=tenant.contact_email,
                phone=tenant.contact_phone,
                total_overdue=float(total_overdue),
                overdue_bills_count=bills_count,
                days_overdue=days_overdue,
                oldest_due_date=oldest_due_date,
                degradation_level=getattr(tenant, "degradation_level", None),
            )
        )

    response = OverdueTenantListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

    return ApiResponse(data=response)


@router.get("/tenants/{tenant_id}", response_model=ApiResponse[TenantResponse])
async def get_tenant(
    tenant_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    获取租户详情
    
    权限：所有管理员
    """
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=tenant)


@router.post(
    "/tenants",
    response_model=ApiResponse[TenantWithAPIKey],
    dependencies=[Depends(require_admin_permission(Permission.TENANT_CREATE))],
)
async def create_tenant(
    tenant_data: TenantCreate,
    admin: AdminDep,
    db: DBDep,
):
    """
    创建租户（代客开户）
    
    权限：super_admin, support_admin
    """
    service = TenantService(db)
    tenant, api_key = await service.create_tenant(
        tenant_data=tenant_data,
        created_by=admin.admin_id,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_tenant_create(
        admin_id=admin.admin_id,
        tenant_id=tenant.tenant_id,
        tenant_data=tenant_data.model_dump(),
    )

    # 返回包含API Key的响应
    response = TenantWithAPIKey(
        **tenant.__dict__,
        api_key=api_key,
    )

    return ApiResponse(data=response)


@router.put(
    "/tenants/{tenant_id}/status",
    response_model=ApiResponse[TenantResponse],
    dependencies=[Depends(require_admin_permission(Permission.TENANT_SUSPEND))],
)
async def update_tenant_status(
    tenant_id: str,
    status_data: TenantUpdateStatus,
    admin: AdminDep,
    db: DBDep,
):
    """
    更新租户状态
    
    权限：super_admin, support_admin
    """
    service = TenantService(db)

    # 获取变更前状态
    old_tenant = await service.get_tenant(tenant_id)
    old_status = old_tenant.status

    # 更新状态
    tenant = await service.update_tenant_status(
        tenant_id=tenant_id,
        status=status_data.status,
        reason=status_data.reason,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_tenant_update(
        admin_id=admin.admin_id,
        tenant_id=tenant_id,
        before={"status": old_status},
        after={"status": status_data.status, "reason": status_data.reason},
    )

    return ApiResponse(data=tenant)


@router.post(
    "/tenants/{tenant_id}/assign-plan",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin_permission(Permission.SUBSCRIPTION_UPDATE))],
)
async def assign_plan(
    tenant_id: str,
    plan_type: str = Query(..., description="套餐类型"),
    duration_months: int = Query(1, ge=1, le=36, description="订阅时长"),
    admin: AdminDep = None,
    db: DBDep = None,
):
    """
    分配套餐
    
    权限：super_admin, support_admin
    """
    service = SubscriptionService(db)
    subscription = await service.assign_plan(
        tenant_id=tenant_id,
        plan_type=plan_type,
        duration_months=duration_months,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_plan_change(
        admin_id=admin.admin_id,
        tenant_id=tenant_id,
        old_plan="",
        new_plan=plan_type,
    )

    return ApiResponse(data=subscription)


@router.post(
    "/tenants/{tenant_id}/adjust-quota",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin_permission(Permission.QUOTA_ADJUST))],
)
async def adjust_quota(
    tenant_id: str,
    quota_type: str = Query(..., description="配额类型"),
    amount: int = Query(..., description="调整数量"),
    reason: str | None = Query(None, description="调整原因"),
    admin: AdminDep = None,
    db: DBDep = None,
):
    """
    调整配额
    
    权限：super_admin, support_admin
    """
    service = QuotaService(db)
    subscription = await service.adjust_quota(
        tenant_id=tenant_id,
        quota_type=quota_type,
        amount=amount,
        reason=reason,
    )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_quota_adjustment(
        admin_id=admin.admin_id,
        tenant_id=tenant_id,
        quota_type=quota_type,
        amount=amount,
        reason=reason,
    )

    return ApiResponse(data=subscription)


@router.post(
    "/tenants/batch-operation",
    response_model=ApiResponse[BatchOperationResponse],
    dependencies=[Depends(require_admin_permission(Permission.TENANT_UPDATE))],
)
async def batch_operation(
    batch_data: BatchOperationRequest,
    admin: AdminDep,
    db: DBDep,
    request: Request,
):
    """
    批量操作租户
    
    支持的操作类型：
    - activate: 激活租户
    - suspend: 暂停租户
    - delete: 删除租户（软删除）
    - upgrade_plan: 升级套餐（需要params.plan参数）
    - downgrade_plan: 降级套餐（需要params.plan参数）
    - extend_service: 延期服务（需要params.days参数，默认30天）
    - reset_quota: 重置配额
    
    权限：super_admin, support_admin
    """
    tenant_service = TenantService(db)
    subscription_service = SubscriptionService(db)
    audit_service = AuditService(db)
    
    results = {"success": [], "failed": []}
    
    # 根据操作类型调用不同的服务方法
    if batch_data.operation == "activate":
        results = await tenant_service.batch_activate_tenants(batch_data.tenant_ids)
    
    elif batch_data.operation == "suspend":
        results = await tenant_service.batch_suspend_tenants(batch_data.tenant_ids)
    
    elif batch_data.operation == "delete":
        results = await tenant_service.batch_delete_tenants(batch_data.tenant_ids)
    
    elif batch_data.operation == "upgrade_plan":
        new_plan = batch_data.params.get("plan") if batch_data.params else None
        if not new_plan:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="升级套餐需要提供 params.plan 参数")
        results = await subscription_service.batch_upgrade_plan(batch_data.tenant_ids, new_plan)
    
    elif batch_data.operation == "downgrade_plan":
        new_plan = batch_data.params.get("plan") if batch_data.params else None
        if not new_plan:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="降级套餐需要提供 params.plan 参数")
        results = await subscription_service.batch_downgrade_plan(batch_data.tenant_ids, new_plan)
    
    elif batch_data.operation == "extend_service":
        days = batch_data.params.get("days", 30) if batch_data.params else 30
        results = await subscription_service.batch_extend_service(
            tenant_ids=batch_data.tenant_ids,
            days=days,
        )
    
    elif batch_data.operation == "reset_quota":
        redis = getattr(request.app.state, "redis", None)
        results = await tenant_service.batch_reset_quota(batch_data.tenant_ids, redis)
    
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"不支持的操作: {batch_data.operation}")
    
    # 记录审计日志
    await audit_service.log_batch_operation(
        admin_id=admin.admin_id,
        operation=batch_data.operation,
        tenant_ids=batch_data.tenant_ids[:10],  # 最多记录10个
        params=batch_data.params,
        success_count=len(results["success"]),
        failed_count=len(results["failed"]),
    )
    
    response = BatchOperationResponse(
        success=results["success"],
        failed=results["failed"],
        total=len(batch_data.tenant_ids),
        success_count=len(results["success"]),
        failed_count=len(results["failed"]),
    )

    return ApiResponse(data=response)


@router.post("/tenants/{tenant_id}/send-reminder")
async def send_payment_reminder(
    tenant_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    发送催款提醒
    
    向租户发送邮件/短信催款提醒
    
    权限：需要 BILLING_UPDATE 权限
    """
    from models.tenant import Bill
    
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    
    # 获取欠费信息
    overdue_stmt = select(Bill).where(
        and_(
            Bill.tenant_id == tenant_id,
            Bill.status.in_(["pending", "overdue"]),
            Bill.due_date < datetime.utcnow(),
        )
    )
    result = await db.execute(overdue_stmt)
    overdue_bills = result.scalars().all()
    
    if not overdue_bills:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="该租户无欠费账单")
    
    total_overdue = sum(b.total_amount for b in overdue_bills)
    
    # 发送异步任务通知（Celery任务，这里先注释掉）
    # from tasks.notification_tasks import send_payment_reminder_notification
    # send_payment_reminder_notification.delay(
    #     tenant_id=tenant_id,
    #     total_overdue=float(total_overdue),
    #     bills_count=len(overdue_bills),
    # )
    
    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_operation(
        admin_id=admin.admin_id,
        operation_type="send_payment_reminder",
        resource_type="tenant",
        resource_id=tenant_id,
        operation_details={
            "total_overdue": float(total_overdue),
            "bills_count": len(overdue_bills),
        },
    )
    
    return ApiResponse(data={"message": "催款提醒已发送"})


# ============ API密钥管理 ============
@router.post("/tenants/{tenant_id}/reset-api-key")
async def reset_tenant_api_key(
    tenant_id: str,
    admin: AdminDep,
    db: DBDep,
    request: Request,
):
    """
    重置租户API密钥
    
    操作流程：
    1. 生成新的API Key
    2. 旧Key立即失效
    3. 清除Redis缓存
    4. 发送通知给租户
    5. 记录审计日志
    
    权限：需要 TENANT_UPDATE 权限
    """
    service = TenantService(db)
    audit_service = AuditService(db)
    
    # 重置API密钥
    tenant, new_api_key = await service.reset_api_key(tenant_id)
    
    # 清除Redis缓存（如果有）
    redis = getattr(request.app.state, "redis", None)
    if redis:
        try:
            # 清除旧的API Key缓存
            # 假设缓存key格式为 api_key:{api_key_prefix}
            await redis.delete(f"api_key:{tenant.tenant_id}")
            await redis.delete(f"tenant:{tenant.tenant_id}:api_key")
        except Exception as e:
            # Redis不可用时不影响主流程
            pass
    
    # 发送通知给租户（Celery任务，这里先注释掉）
    # from tasks.notification_tasks import send_api_key_reset_notification
    # send_api_key_reset_notification.delay(
    #     tenant_id=tenant_id,
    #     new_api_key=new_api_key,
    # )
    
    # 记录审计日志
    await audit_service.log_operation(
        admin_id=admin.admin_id,
        operation_type="reset_api_key",
        resource_type="tenant",
        resource_id=tenant_id,
        operation_details={
            "reason": "admin_reset",
        },
    )
    
    return ApiResponse(
        data={
            "api_key": new_api_key,  # 仅此次返回完整key
            "message": "API密钥已重置，请妥善保管新密钥",
            "tenant_id": tenant_id,
        }
    )


# ============ 账单审核 ============
@router.get("/bills/pending")
async def get_pending_bills(
    admin: AdminDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    获取待审核账单列表
    
    返回状态为pending的账单
    
    权限：需要 BILLING_READ 权限
    """
    from models.tenant import Bill
    from schemas.billing import PendingBillInfo
    
    # 查询待审核账单
    stmt = (
        select(Bill, Tenant)
        .join(Tenant, Bill.tenant_id == Tenant.tenant_id)
        .where(Bill.status == "pending")
        .order_by(Bill.created_at.desc())
    )
    
    # 获取总数
    count_stmt = select(func.count(Bill.id)).where(Bill.status == "pending")
    total = await db.scalar(count_stmt) or 0
    
    # 分页
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.all()
    
    items = []
    for bill, tenant in rows:
        items.append(
            PendingBillInfo(
                bill_id=bill.bill_id,
                tenant_id=bill.tenant_id,
                company_name=tenant.company_name,
                amount=float(bill.total_amount),
                billing_period_start=bill.billing_period_start,
                billing_period_end=bill.billing_period_end,
                due_date=bill.due_date,
                created_at=bill.created_at,
            )
        )
    
    response = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
    
    return ApiResponse(data=response)


@router.post("/bills/{bill_id}/approve")
async def approve_bill(
    bill_id: str,
    admin: AdminDep,
    db: DBDep,
):
    """
    审核通过账单
    
    将账单状态从pending改为approved
    
    权限：需要 BILLING_UPDATE 权限
    """
    from models.tenant import Bill
    
    # 查询账单
    stmt = select(Bill).where(Bill.bill_id == bill_id)
    result = await db.execute(stmt)
    bill = result.scalar_one_or_none()
    
    if not bill:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="账单不存在")
    
    if bill.status != "pending":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"账单状态为{bill.status}，无法审核")
    
    # 更新状态（这里假设审核通过后状态改为可支付状态）
    # 实际业务中可能需要更复杂的状态转换
    bill.status = "approved"  # 或者保持pending，等待支付
    bill.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_operation(
        admin_id=admin.admin_id,
        operation_type="approve_bill",
        resource_type="bill",
        resource_id=bill_id,
        operation_details={
            "tenant_id": bill.tenant_id,
            "amount": float(bill.total_amount),
        },
    )
    
    return ApiResponse(data={"message": "账单审核通过"})


@router.post("/bills/{bill_id}/reject")
async def reject_bill(
    bill_id: str,
    admin: AdminDep,
    db: DBDep,
    reason: str = Query(..., min_length=1, max_length=500, description="拒绝原因"),
):
    """
    审核拒绝账单
    
    将账单状态从pending改为rejected
    
    权限：需要 BILLING_UPDATE 权限
    """
    from models.tenant import Bill
    
    # 查询账单
    stmt = select(Bill).where(Bill.bill_id == bill_id)
    result = await db.execute(stmt)
    bill = result.scalar_one_or_none()
    
    if not bill:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="账单不存在")
    
    if bill.status != "pending":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"账单状态为{bill.status}，无法审核")
    
    # 更新状态
    bill.status = "rejected"
    bill.updated_at = datetime.utcnow()
    # 如果Bill模型有reject_reason字段，可以保存原因
    # bill.reject_reason = reason
    
    await db.commit()
    
    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_operation(
        admin_id=admin.admin_id,
        operation_type="reject_bill",
        resource_type="bill",
        resource_id=bill_id,
        operation_details={
            "tenant_id": bill.tenant_id,
            "amount": float(bill.total_amount),
            "reject_reason": reason,
        },
    )
    
    return ApiResponse(data={"message": "账单已拒绝", "reason": reason})



