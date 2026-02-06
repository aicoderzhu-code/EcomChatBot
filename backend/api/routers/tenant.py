"""
租户管理 API 路由（租户自用）
"""
from datetime import timedelta

from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantDep, TenantTokenDep
from core import create_access_token, settings
from schemas import (
    ApiResponse,
    PaginatedResponse,
    QuotaUsageResponse,
    SubscriptionResponse,
    TenantLoginRequest,
    TenantLoginResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    TenantResponse,
    UsageRecordResponse,
)
from services import QuotaService, SubscriptionService, TenantService, UsageService

router = APIRouter(prefix="/tenant", tags=["租户管理"])


@router.post("/register", response_model=ApiResponse[TenantRegisterResponse])
async def register_tenant(
    register_data: TenantRegisterRequest,
    db: DBDep,
):
    """
    租户自助注册

    - **company_name**: 公司名称
    - **contact_name**: 联系人姓名
    - **contact_email**: 联系邮箱（用于登录）
    - **contact_phone**: 联系电话（可选）
    - **password**: 密码（至少8位）

    返回租户ID和API Key，请妥善保存API Key，仅显示一次。
    """
    service = TenantService(db)
    tenant_id, api_key = await service.register_tenant(register_data)
    return ApiResponse(
        data=TenantRegisterResponse(
            tenant_id=tenant_id,
            api_key=api_key,
            message="注册成功，请妥善保存API Key"
        )
    )


@router.post("/login", response_model=ApiResponse[TenantLoginResponse])
async def login_tenant(
    login_data: TenantLoginRequest,
    db: DBDep,
):
    """
    租户登录获取JWT Token

    - **email**: 注册时使用的邮箱
    - **password**: 密码

    返回JWT Token和租户ID，Token有效期为24小时。
    """
    service = TenantService(db)
    tenant_id = await service.authenticate_tenant(login_data.email, login_data.password)

    # 创建JWT Token
    access_token = create_access_token(
        subject=tenant_id,
        tenant_id=tenant_id,
        expires_delta=timedelta(hours=24)
    )

    return ApiResponse(
        data=TenantLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,  # 24小时
            tenant_id=tenant_id
        )
    )


@router.get("/info", response_model=ApiResponse[TenantResponse])
async def get_tenant_info(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取租户信息（支持API Key认证）"""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=TenantResponse.model_validate(tenant))


@router.get("/info-token", response_model=ApiResponse[TenantResponse])
async def get_tenant_info_token(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取租户信息（支持JWT Token认证）"""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=TenantResponse.model_validate(tenant))


@router.get("/subscription", response_model=ApiResponse[SubscriptionResponse])
async def get_subscription(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取订阅信息（支持API Key认证）"""
    service = SubscriptionService(db)
    subscription = await service.get_subscription(tenant_id)
    return ApiResponse(data=subscription)


@router.get("/subscription-token", response_model=ApiResponse[SubscriptionResponse])
async def get_subscription_token(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取订阅信息（支持JWT Token认证）"""
    service = SubscriptionService(db)
    subscription = await service.get_subscription(tenant_id)
    return ApiResponse(data=subscription)


@router.get("/usage", response_model=ApiResponse[dict])
async def get_usage(
    tenant_id: TenantDep,
    db: DBDep,
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
):
    """获取用量统计"""
    service = UsageService(db)
    usage = await service.get_usage_summary(tenant_id, year, month)
    return ApiResponse(data=usage)


@router.get("/quota", response_model=ApiResponse[QuotaUsageResponse])
async def get_quota_usage(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取配额使用情况"""
    service = QuotaService(db)
    quota = await service.get_quota_usage(tenant_id)
    return ApiResponse(data=quota)


@router.post("/subscription/upgrade", response_model=ApiResponse[SubscriptionResponse])
async def upgrade_subscription(
    tenant_id: TenantTokenDep,
    new_plan: str = Query(..., description="目标套餐类型 (free/basic/professional/enterprise)"),
    db: DBDep = None,
):
    """
    升级/变更订阅套餐

    - **new_plan**: 目标套餐类型
      - free: 免费版 (100次对话/月)
      - basic: 基础版 (1000次对话/月)
      - professional: 专业版 (10000次对话/月)
      - enterprise: 企业版 (无限制)

    变更立即生效，配额将按新套餐标准调整。
    """
    # 验证套餐类型
    valid_plans = ["free", "basic", "professional", "enterprise"]
    if new_plan not in valid_plans:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的套餐类型，可选值: {', '.join(valid_plans)}",
        )

    service = SubscriptionService(db)
    subscription = await service.change_plan(
        tenant_id=tenant_id,
        new_plan=new_plan,
        effective_date=None,  # 立即生效
    )

    return ApiResponse(data=subscription)
