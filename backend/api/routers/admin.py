"""
管理员 API 路由（平台管理）
"""
from fastapi import APIRouter, Depends, Query

from api.dependencies import AdminDep, DBDep, require_admin_permission
from core import AdminRole, Permission, create_access_token
from schemas import (
    AdminCreate,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminResponse,
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

    # 生成Token
    token = create_access_token(
        subject=admin.admin_id,
        role=admin.role,
    )

    # 使用 model_validate 序列化 ORM 对象
    response = AdminLoginResponse.model_validate({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 28800,  # 8小时
        "admin": AdminResponse.model_validate(admin)
    })

    return ApiResponse(data=response)


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
):
    """
    批量操作
    
    权限：super_admin, support_admin
    """
    if batch_data.operation == "extend_service":
        days = batch_data.params.get("days", 30)
        service = SubscriptionService(db)
        results = await service.batch_extend_service(
            tenant_ids=batch_data.tenant_ids,
            days=days,
        )

        response = BatchOperationResponse(
            success=results["success"],
            failed=results["failed"],
            total=len(batch_data.tenant_ids),
            success_count=len(results["success"]),
            failed_count=len(results["failed"]),
        )

        return ApiResponse(data=response)

    from fastapi import HTTPException

    raise HTTPException(status_code=400, detail=f"不支持的操作: {batch_data.operation}")
