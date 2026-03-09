"""
租户管理 API 路由（租户自用）
"""
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Query, HTTPException, status

from api.dependencies import DBDep, TenantFlexDep, TenantTokenDep
from core import create_access_token, settings
from schemas import (
    ApiResponse,
    PaginatedResponse,
    ResetApiKeyResponse,
    SubscriptionResponse,
    TenantLoginRequest,
    TenantLoginResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    TenantResponse,
    SubscribePlanRequest,
    ChangePlanRequest,
    SubscriptionDetail,
    ProratedPriceDetail,
    SubscriptionOperationResponse,
)
from services import SubscriptionService, TenantService
from services.payment_service import PaymentService, PLAN_CONFIG
from models.payment import PaymentType, SubscriptionType

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
    result = await service.authenticate_tenant(login_data.email, login_data.password)

    # authenticate_tenant 可能返回 Tenant 对象或 tenant_id 字符串
    tenant_id = result.tenant_id if hasattr(result, "tenant_id") else result

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
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取租户信息（支持API Key和JWT Token认证）"""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=tenant)


@router.get("/info-token", response_model=ApiResponse[TenantResponse])
async def get_tenant_info_token(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取租户信息（支持JWT Token认证）"""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return ApiResponse(data=tenant)


@router.post("/reset-api-key", response_model=ApiResponse[ResetApiKeyResponse])
async def reset_api_key(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """
    租户自助重置 API Key

    重置后旧 Key 立即失效，新 Key 仅在响应中返回一次，请妥善保存。
    需要 JWT Token 认证（登录后可用）。
    """
    service = TenantService(db)
    tenant, new_api_key = await service.reset_api_key(tenant_id)
    return ApiResponse(
        data=ResetApiKeyResponse(
            api_key=new_api_key,
            api_key_prefix=tenant.api_key_prefix or new_api_key[:12],
        )
    )


@router.get("/subscription", response_model=ApiResponse[SubscriptionResponse])
async def get_subscription(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取订阅信息（支持API Key和JWT Token认证）"""
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


@router.get("/subscription/status", response_model=ApiResponse[dict])
async def get_subscription_status(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取订阅状态（含宽限期信息，JWT Token认证）"""
    service = SubscriptionService(db)
    status_info = await service.get_subscription_with_grace(tenant_id)
    return ApiResponse(data=status_info)


# ============ 套餐订阅 API ============

@router.post("/subscribe", response_model=ApiResponse[SubscriptionOperationResponse])
async def subscribe_plan(
    request: SubscribePlanRequest,
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """
    订阅套餐

    - **plan_type**: 套餐类型 (basic/professional/enterprise)
    - **duration_months**: 订阅时长（月），1-36个月
    - **payment_method**: 支付方式 (alipay)
    - **auto_renew**: 是否自动续费

    流程：
    1. 验证套餐有效性
    2. 如果是免费套餐，直接激活
    3. 如果是付费套餐，创建支付订单并返回支付链接
    """
    # 验证套餐类型
    valid_plans = ["free", "basic", "professional", "enterprise"]
    if request.plan_type not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的套餐类型，可选值: {', '.join(valid_plans)}"
        )

    subscription_service = SubscriptionService(db)
    tenant_service = TenantService(db)

    # 获取租户信息
    tenant = await tenant_service.get_tenant(tenant_id)

    # 如果是免费套餐，直接激活
    if request.plan_type == "free":
        subscription = await subscription_service.assign_plan(
            tenant_id=tenant_id,
            plan_type="free",
            duration_months=12,  # 免费套餐默认一年
            auto_renew=False,
        )
        return ApiResponse(
            data=SubscriptionOperationResponse(
                success=True,
                message="免费套餐已激活",
                subscription=SubscriptionDetail.model_validate(subscription),
                payment_required=False,
            )
        )

    # 付费套餐：创建支付宝支付订单
    payment_service = PaymentService(db)
    order, qr_url = await payment_service.create_native_payment_order(
        tenant_id=tenant.id,
        plan_type=request.plan_type,
        subscription_type=SubscriptionType.NEW,
        description=f"{request.plan_type}套餐订阅",
    )

    return ApiResponse(
        data=SubscriptionOperationResponse(
            success=True,
            message="订单创建成功，请扫码完成支付",
            order_number=order.order_number,
            payment_required=True,
            payment_amount=order.amount,
        )
    )


@router.put("/subscription", response_model=ApiResponse[SubscriptionOperationResponse])
async def change_plan(
    request: ChangePlanRequest,
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """
    变更套餐（升级/降级）

    - **new_plan_type**: 新套餐类型 (basic/professional/enterprise)
    - **effective_immediately**: 是否立即生效

    规则：
    - 升级：立即生效，按比例计算差价
    - 降级：下个计费周期生效
    """
    # 验证套餐类型
    valid_plans = ["free", "basic", "professional", "enterprise"]
    if request.new_plan_type not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的套餐类型，可选值: {', '.join(valid_plans)}"
        )

    subscription_service = SubscriptionService(db)
    tenant_service = TenantService(db)
    payment_service = PaymentService(db)

    # 获取当前订阅
    current_subscription = await subscription_service.get_subscription(tenant_id)
    current_plan = current_subscription.plan_type

    # 获取租户信息
    tenant = await tenant_service.get_tenant(tenant_id)

    # 如果新套餐和当前套餐相同
    if request.new_plan_type == current_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新套餐与当前套餐相同"
        )

    # 获取套餐价格（用于判断升降级）
    current_price = PLAN_CONFIG.get(current_plan, (Decimal("0"), 0))[0]
    new_price = PLAN_CONFIG.get(request.new_plan_type, (Decimal("0"), 0))[0]

    # 判断是升级还是降级
    is_upgrade = new_price > current_price

    if is_upgrade and request.effective_immediately:
        # 升级且立即生效：计算差价
        prorated_info = await subscription_service.calculate_prorated_price(
            tenant_id=tenant_id,
            new_plan=request.new_plan_type,
        )

        prorated_charge = Decimal(str(prorated_info["prorated_charge"]))

        if prorated_charge > 0:
            # 需要补差价，创建支付订单
            order, qr_url = await payment_service.create_native_payment_order(
                tenant_id=tenant.id,
                plan_type=request.new_plan_type,
                subscription_type=SubscriptionType.UPGRADE,
                description=f"套餐升级: {current_plan} -> {request.new_plan_type}",
            )
            # 更新订单金额为差价
            order.amount = prorated_charge
            await db.commit()

            return ApiResponse(
                data=SubscriptionOperationResponse(
                    success=True,
                    message=f"需补差价 ¥{prorated_charge}，请完成支付后套餐将立即升级",
                    order_number=order.order_number,
                    payment_required=True,
                    payment_amount=prorated_charge,
                )
            )
        else:
            # 不需要补差价，直接升级
            subscription = await subscription_service.change_plan(
                tenant_id=tenant_id,
                new_plan=request.new_plan_type,
                effective_date=None,  # 立即生效
            )
            return ApiResponse(
                data=SubscriptionOperationResponse(
                    success=True,
                    message="套餐已升级",
                    subscription=SubscriptionDetail.model_validate(subscription),
                    payment_required=False,
                )
            )
    else:
        # 降级或延期生效：下个周期生效
        subscription = await subscription_service.change_plan(
            tenant_id=tenant_id,
            new_plan=request.new_plan_type,
            effective_date=current_subscription.expire_at,
        )
        return ApiResponse(
            data=SubscriptionOperationResponse(
                success=True,
                message=f"套餐变更已安排，将在 {current_subscription.expire_at.strftime('%Y-%m-%d')} 生效",
                subscription=SubscriptionDetail.model_validate(subscription),
                payment_required=False,
            )
        )


@router.get("/subscription/price-preview", response_model=ApiResponse[ProratedPriceDetail])
async def preview_plan_change_price(
    new_plan_type: str = Query(..., description="新套餐类型"),
    tenant_id: TenantTokenDep = None,
    db: DBDep = None,
):
    """
    预览套餐变更价格

    返回升级差价的详细计算信息，包括：
    - 当前套餐剩余价值
    - 新套餐剩余价值
    - 需补差价
    - 剩余天数
    """
    # 验证套餐类型
    valid_plans = ["basic", "professional", "enterprise"]
    if new_plan_type not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的套餐类型，可选值: {', '.join(valid_plans)}"
        )

    subscription_service = SubscriptionService(db)

    try:
        prorated_info = await subscription_service.calculate_prorated_price(
            tenant_id=tenant_id,
            new_plan=new_plan_type,
        )
        return ApiResponse(
            data=ProratedPriceDetail(
                current_plan=prorated_info["current_plan"],
                new_plan=prorated_info["new_plan"],
                current_plan_value=Decimal(str(prorated_info["current_plan_value"])),
                new_plan_value=Decimal(str(prorated_info["new_plan_value"])),
                prorated_charge=Decimal(str(prorated_info["prorated_charge"])),
                remaining_days=prorated_info["remaining_days"],
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
