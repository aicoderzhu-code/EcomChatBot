"""
支付 API 路由

提供支付相关的HTTP接口（支付宝官方 API 版本）
"""
import logging
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import TenantDep, DBDep
from models.payment import SubscriptionType, PaymentChannel
from schemas.base import ApiResponse
from services.payment_service import PaymentService, PLAN_CONFIG
from services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["支付管理"])


# ===== 请求/响应 Schema =====

class CreateOrderRequest(BaseModel):
    plan_type: str
    subscription_type: str = "new"   # "new" | "renewal" | "upgrade"
    payment_channel: str = "alipay"  # "alipay" | "wechat"
    description: Optional[str] = None


class RefundRequest(BaseModel):
    refund_amount: Optional[Decimal] = None
    refund_reason: str = "用户申请退款"


# ===== 订单接口 =====

@router.post("/orders/create", summary="创建扫码支付订单")
async def create_payment_order(
    request_data: CreateOrderRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    创建扫码支付订单（支持支付宝和微信支付）

    **请求参数**:
    - plan_type: 套餐类型（monthly/quarterly/semi_annual/annual）
    - subscription_type: 订阅类型（new/renewal/upgrade）
    - payment_channel: 支付渠道（alipay/wechat）

    **响应**:
    - order_number: 订单编号
    - amount: 金额
    - qr_code_url: 二维码URL（前端展示）
    - expires_at: 过期时间
    """
    if request_data.plan_type not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail=f"无效的套餐类型: {request_data.plan_type}")

    # 验证支付渠道
    channel_map = {"alipay": PaymentChannel.ALIPAY, "wechat": PaymentChannel.WECHAT}
    channel = channel_map.get(request_data.payment_channel, PaymentChannel.ALIPAY)

    try:
        sub_type_map = {
            "new": SubscriptionType.NEW,
            "renewal": SubscriptionType.RENEWAL,
            "upgrade": SubscriptionType.UPGRADE,
        }
        subscription_type = sub_type_map.get(request_data.subscription_type, SubscriptionType.NEW)

        payment_service = PaymentService(db, channel=channel)
        order, qr_url = await payment_service.create_native_payment_order(
            tenant_id=tenant_id,
            plan_type=request_data.plan_type,
            subscription_type=subscription_type,
            payment_channel=channel,
            description=request_data.description,
        )

        return ApiResponse(data={
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": float(order.amount),
            "currency": order.currency,
            "payment_channel": channel.value,
            "qr_code_url": qr_url,
            "expires_at": order.expired_at.isoformat(),
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment order: {e}")
        raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")


@router.get("/orders/{order_number}", summary="查询订单详情")
async def get_order_detail(
    order_number: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """查询订单详情，PENDING 状态会主动向网关同步"""
    try:
        payment_service = PaymentService(db)
        order_info = await payment_service.query_order_status(order_number)

        if not order_info:
            raise HTTPException(status_code=404, detail="订单不存在")

        return ApiResponse(data=order_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order detail: {e}")
        raise HTTPException(status_code=500, detail=f"查询订单失败: {str(e)}")


@router.post("/orders/{order_number}/sync", summary="主动同步订单状态")
async def sync_order_status(
    order_number: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """主动向支付宝查询最新状态并更新本地订单"""
    try:
        payment_service = PaymentService(db)
        order_info = await payment_service.query_order_status(order_number)

        if not order_info:
            raise HTTPException(status_code=404, detail="订单不存在")

        return ApiResponse(data={"message": "订单状态已同步", "order": order_info})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing order status: {e}")
        raise HTTPException(status_code=500, detail=f"同步订单状态失败: {str(e)}")


@router.post("/orders/{order_number}/refund", summary="申请退款")
async def refund_order(
    order_number: str,
    refund_data: RefundRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """申请退款"""
    try:
        payment_service = PaymentService(db)
        result = await payment_service.refund_order(
            order_number=order_number,
            refund_amount=refund_data.refund_amount,
            refund_reason=refund_data.refund_reason,
        )
        return ApiResponse(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        raise HTTPException(status_code=500, detail=f"退款失败: {str(e)}")


# ===== 支付宝异步回调 =====

@router.post("/callback/alipay/notify", summary="支付宝异步回调")
async def alipay_notify_callback(
    request: Request,
    db: DBDep,
):
    """
    支付宝异步回调处理

    支付宝会POST以下参数：
    - out_trade_no: 商户订单号
    - trade_no: 支付宝交易号
    - trade_status: 交易状态
    - total_amount: 订单金额
    - sign: 签名
    """
    try:
        form_data = await request.form()
        notify_data = dict(form_data)

        logger.info(f"Received alipay notify: {notify_data.get('out_trade_no')}")

        payment_service = PaymentService(db)
        success = await payment_service.handle_alipay_notify(notify_data)

        if success:
            return Response(content="success", media_type="text/plain")
        else:
            return Response(content="fail", media_type="text/plain", status_code=400)

    except Exception as e:
        logger.error(f"Error handling alipay notify: {e}")
        return Response(content="fail", media_type="text/plain", status_code=500)


@router.post("/callback/wechat/notify", summary="微信支付异步回调")
async def wechat_pay_notify(request: Request, db: DBDep):
    """
    接收微信支付异步通知

    微信支付会POST加密的JSON数据，需要验签和解密。
    返回格式: {"code": "SUCCESS", "message": "成功"}
    """
    try:
        body = await request.body()
        headers = dict(request.headers)

        # 解析JSON
        import json
        notify_data = json.loads(body.decode("utf-8"))

        logger.info(f"Received wechat notify: event_type={notify_data.get('event_type')}")

        payment_service = PaymentService(db, channel=PaymentChannel.WECHAT)
        success = await payment_service.handle_wechat_notify(notify_data, headers)

        if success:
            return {"code": "SUCCESS", "message": "成功"}
        else:
            return Response(
                status_code=400,
                content='{"code":"FAIL","message":"处理失败"}',
                media_type="application/json"
            )
    except Exception as e:
        logger.error(f"Wechat notify error: {e}")
        return Response(
            status_code=500,
            content='{"code":"FAIL","message":"系统错误"}',
            media_type="application/json"
        )


# ===== 订单列表（管理员） =====

@router.get("/orders", summary="获取支付订单列表")
async def list_payment_orders(
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
):
    """获取支付订单列表（管理员接口）"""
    from sqlalchemy import and_, func, select
    from models.payment import PaymentOrder
    from models import Tenant

    order_conditions = []
    tenant_conditions = []

    if status:
        order_conditions.append(PaymentOrder.status == status)
    if tenant_id:
        tenant_conditions.append(Tenant.tenant_id == tenant_id)

    all_conditions = order_conditions + tenant_conditions

    count_query = (
        select(func.count(PaymentOrder.id))
        .select_from(PaymentOrder)
        .join(Tenant, PaymentOrder.tenant_id == Tenant.id)
    )
    if all_conditions:
        count_query = count_query.where(and_(*all_conditions))
    total = await db.scalar(count_query) or 0

    query = select(PaymentOrder, Tenant).join(Tenant, PaymentOrder.tenant_id == Tenant.id)
    if all_conditions:
        query = query.where(and_(*all_conditions))
    query = query.order_by(PaymentOrder.created_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for order, tenant in rows:
        items.append({
            "id": order.id,
            "order_number": order.order_number,
            "tenant_id": order.tenant_id,
            "company_name": tenant.company_name,
            "amount": float(order.amount),
            "currency": order.currency,
            "status": order.status,
            "plan_type": order.plan_type,
            "payment_channel": order.payment_channel,
            "qr_code_url": order.qr_code_url,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "expired_at": order.expired_at.isoformat() if order.expired_at else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    })


# ===== 订阅管理接口 =====

@router.get("/subscription", summary="获取订阅详情")
async def get_subscription(
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取当前订阅详情"""
    try:
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_subscription(tenant_id)

        import json as _json
        features = subscription.enabled_features
        if isinstance(features, str):
            features = _json.loads(features)

        from schemas.subscription import SubscriptionDetail
        return SubscriptionDetail(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_type=subscription.plan_type,
            status=subscription.status,
            start_date=subscription.start_date,
            expire_at=subscription.expire_at,
            auto_renew=subscription.auto_renew,
            is_trial=subscription.is_trial,
            enabled_features=features,
            pending_plan=subscription.pending_plan,
            plan_change_date=subscription.plan_change_date,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail=f"获取订阅详情失败: {str(e)}")


@router.post("/subscription/subscribe", summary="订阅套餐")
async def subscribe_plan(
    request_data: CreateOrderRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """订阅套餐，创建扫码支付订单"""
    if request_data.plan_type not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail=f"无效的套餐类型: {request_data.plan_type}")

    try:
        payment_service = PaymentService(db)
        order, qr_url = await payment_service.create_native_payment_order(
            tenant_id=tenant_id,
            plan_type=request_data.plan_type,
            subscription_type=SubscriptionType.NEW,
            description=f"订阅{request_data.plan_type}套餐",
        )

        return ApiResponse(data={
            "success": True,
            "message": "订单创建成功，请扫码完成支付",
            "order_number": order.order_number,
            "payment_required": True,
            "payment_amount": float(order.amount),
            "qr_code_url": qr_url,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing plan: {e}")
        raise HTTPException(status_code=500, detail=f"订阅套餐失败: {str(e)}")


@router.put("/subscription/change", summary="变更套餐")
async def change_plan(
    new_plan_type: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """变更套餐（升级需支付差价，降级下周期生效）"""
    try:
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_subscription(tenant_id)

        if subscription.plan_type == new_plan_type:
            raise HTTPException(status_code=400, detail="新套餐与当前套餐相同")

        plan_order = ["trial", "monthly", "quarterly", "semi_annual", "annual"]
        current_idx = plan_order.index(subscription.plan_type) if subscription.plan_type in plan_order else 0
        new_idx = plan_order.index(new_plan_type) if new_plan_type in plan_order else 0
        is_upgrade = new_idx > current_idx

        if is_upgrade:
            payment_service = PaymentService(db)
            order, qr_url = await payment_service.create_native_payment_order(
                tenant_id=tenant_id,
                plan_type=new_plan_type,
                subscription_type=SubscriptionType.UPGRADE,
                description=f"升级到{new_plan_type}套餐",
            )
            return ApiResponse(data={
                "success": True,
                "message": "请扫码完成支付以完成套餐升级",
                "order_number": order.order_number,
                "payment_required": True,
                "payment_amount": float(order.amount),
                "qr_code_url": qr_url,
            })
        else:
            effective_date = subscription.expire_at
            await subscription_service.change_plan(
                tenant_id=tenant_id,
                new_plan=new_plan_type,
                effective_date=effective_date,
            )
            return ApiResponse(data={
                "success": True,
                "message": f"套餐将在 {effective_date.strftime('%Y-%m-%d')} 降级为 {new_plan_type}",
                "payment_required": False,
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing plan: {e}")
        raise HTTPException(status_code=500, detail=f"变更套餐失败: {str(e)}")
