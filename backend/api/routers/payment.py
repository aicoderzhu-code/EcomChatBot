"""
支付 API 路由

提供支付相关的HTTP接口
"""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import TenantDep, DBDep
from models.payment import PaymentType, SubscriptionType
from schemas.payment import (
    CreatePaymentResponse,
    PaymentOrderCreate,
    PaymentOrderDetail,
    RefundRequest,
    RefundResponse,
)
from schemas.subscription import (
    SubscribePlanRequest,
    ChangePlanRequest,
    SubscriptionDetail,
    SubscriptionResponse,
    ProratedPriceDetail,
)
from services.payment_service import PaymentService
from services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["支付管理"])


@router.post("/orders/create", response_model=CreatePaymentResponse, summary="创建支付订单")
async def create_payment_order(
    payment_data: PaymentOrderCreate,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    创建支付订单

    **请求参数**：
    - plan_type: 套餐类型（basic/professional/enterprise）
    - duration_months: 订阅时长（1/3/6/12个月）
    - payment_type: 支付类型（pc/mobile）
    - subscription_type: 订阅类型（new/renewal/upgrade）
    - description: 订单描述（可选）

    **响应**：
    - order_id: 订单ID
    - order_number: 订单编号
    - amount: 订单金额
    - currency: 货币类型
    - payment_html: 支付表单HTML（自动提交）
    - expires_at: 订单过期时间
    """
    try:
        payment_service = PaymentService(db)
        
        # 创建支付订单
        order, payment_html = await payment_service.create_payment_order(
            tenant_id=tenant_id,
            plan_type=payment_data.plan_type,
            duration_months=payment_data.duration_months,
            payment_type=payment_data.payment_type,
            subscription_type=payment_data.subscription_type,
            description=payment_data.description,
        )
        
        return CreatePaymentResponse(
            order_id=order.id,
            order_number=order.order_number,
            amount=order.amount,
            currency=order.currency,
            payment_html=payment_html,
            expires_at=order.expired_at,
        )
        
    except Exception as e:
        logger.error(f"Error creating payment order: {e}")
        raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")


@router.get("/orders/{order_number}", response_model=PaymentOrderDetail, summary="查询订单详情")
async def get_order_detail(
    order_number: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    查询订单详情

    **路径参数**：
    - order_number: 订单编号

    **响应**：
    - 订单完整信息
    """
    try:
        payment_service = PaymentService(db)
        order_info = await payment_service.query_order_status(order_number)
        
        if not order_info:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return order_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order detail: {e}")
        raise HTTPException(status_code=500, detail=f"查询订单失败: {str(e)}")


@router.post("/orders/{order_number}/sync", summary="同步订单状态")
async def sync_order_status(
    order_number: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    主动同步订单状态

    从支付宝查询最新状态并更新本地订单

    **路径参数**：
    - order_number: 订单编号
    """
    try:
        payment_service = PaymentService(db)
        order_info = await payment_service.query_order_status(order_number)
        
        if not order_info:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        return {
            "success": True,
            "message": "订单状态已同步",
            "order": order_info,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing order status: {e}")
        raise HTTPException(status_code=500, detail=f"同步订单状态失败: {str(e)}")


@router.get("/callback/alipay/return", summary="支付宝同步回调（页面跳转）")
async def alipay_return_callback(
    request: Request,
):
    """
    支付宝同步回调（用户支付完成后跳转）

    **功能**：
    - 验证签名
    - 显示支付结果页面
    - **注意**：不在此处理业务逻辑，业务逻辑在异步回调中处理

    **查询参数**：支付宝返回的所有参数
    """
    try:
        # 获取所有查询参数
        params = dict(request.query_params)
        
        logger.info(f"Received alipay return callback: {params.get('out_trade_no')}")
        
        # 这里可以验证签名（可选）
        # 主要用于展示支付结果页面
        # 实际业务处理在异步回调中进行
        
        out_trade_no = params.get("out_trade_no")
        trade_no = params.get("trade_no")
        total_amount = params.get("total_amount")
        
        # 返回支付成功页面（简单HTML）
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>支付结果</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .success-icon {{
                    font-size: 60px;
                    color: #52c41a;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                .info {{
                    color: #666;
                    margin: 10px 0;
                }}
                .button {{
                    display: inline-block;
                    margin-top: 30px;
                    padding: 12px 30px;
                    background-color: #1890ff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>支付处理中</h1>
                <p class="info">订单号: {out_trade_no}</p>
                <p class="info">支付宝交易号: {trade_no}</p>
                <p class="info">支付金额: ¥{total_amount}</p>
                <p style="color: #999; margin-top: 20px;">
                    系统正在处理您的支付，请稍候...
                </p>
                <a href="/" class="button">返回首页</a>
            </div>
            <script>
                // 可以在这里添加订单状态轮询逻辑
                setTimeout(function() {{
                    // 跳转到订单详情页或刷新页面
                    // window.location.href = '/orders/{out_trade_no}';
                }}, 3000);
            </script>
        </body>
        </html>
        """
        
        return Response(content=html_content, media_type="text/html")
        
    except Exception as e:
        logger.error(f"Error in alipay return callback: {e}")
        return Response(
            content=f"<html><body><h1>处理失败</h1><p>{str(e)}</p></body></html>",
            media_type="text/html",
        )


@router.post("/callback/alipay/notify", summary="支付宝异步回调（服务器通知）")
async def alipay_notify_callback(
    request: Request,
    db: DBDep,
):
    """
    支付宝异步回调（服务器到服务器通知）

    **功能**：
    - 验证签名（必须）
    - 更新订单状态
    - 激活订阅
    - 发送通知

    **重要**：
    - 必须返回 "success" 字符串表示处理成功
    - 必须返回 "failure" 字符串表示处理失败
    - 支付宝会重试多次（最多8次）

    **请求体**：支付宝POST的表单数据
    """
    try:
        # 获取表单数据
        form_data = await request.form()
        notify_data = dict(form_data)
        
        logger.info(
            f"Received alipay notify: out_trade_no={notify_data.get('out_trade_no')}, "
            f"trade_no={notify_data.get('trade_no')}, "
            f"trade_status={notify_data.get('trade_status')}"
        )
        
        # 处理异步通知
        payment_service = PaymentService(db)
        success = await payment_service.handle_alipay_notify(notify_data)
        
        if success:
            logger.info(f"Alipay notify processed successfully: {notify_data.get('out_trade_no')}")
            return Response(content="success", media_type="text/plain")
        else:
            logger.error(f"Alipay notify processing failed: {notify_data.get('out_trade_no')}")
            return Response(content="failure", media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Error in alipay notify callback: {e}")
        return Response(content="failure", media_type="text/plain")


@router.post("/orders/{order_number}/refund", response_model=RefundResponse, summary="申请退款")
async def refund_order(
    order_number: str,
    refund_data: RefundRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    申请退款

    **路径参数**：
    - order_number: 订单编号

    **请求参数**：
    - refund_amount: 退款金额（不填则全额退款）
    - refund_reason: 退款原因

    **响应**：
    - refund_id: 退款ID
    - refund_status: 退款状态
    - refund_amount: 退款金额
    - message: 处理消息
    """
    try:
        payment_service = PaymentService(db)
        
        result = await payment_service.refund_order(
            order_number=order_number,
            refund_amount=refund_data.refund_amount,
            refund_reason=refund_data.refund_reason,
        )
        
        return {
            "refund_id": 0,  # 这里可以返回实际的退款ID
            "refund_status": "success",
            "refund_amount": result["refund_amount"],
            "refund_time": "",  # 可以添加实际时间
            "message": result["message"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        raise HTTPException(status_code=500, detail=f"退款失败: {str(e)}")


# ===== 微信支付相关接口 =====

@router.post("/wechat/orders/create", summary="创建微信支付订单")
async def create_wechat_payment_order(
    payment_data: PaymentOrderCreate,
    payment_method: str = Query("native", description="支付方式: native(扫码) 或 jsapi(公众号/小程序)"),
    openid: str | None = Query(None, description="用户openid(JSAPI支付必需)"),
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    创建微信支付订单

    **支付方式**:
    - native: 扫码支付(PC端),返回二维码URL
    - jsapi: 公众号/小程序支付,返回调起支付参数

    **请求参数**:
    - plan_type: 套餐类型(basic/professional/enterprise)
    - duration_months: 订阅时长(1/3/6/12个月)
    - subscription_type: 订阅类型(new/renewal/upgrade)
    - openid: 用户openid(JSAPI支付必需)

    **响应**:
    - Native支付: {"order_number": "...", "code_url": "weixin://..."}
    - JSAPI支付: {"order_number": "...", "appId": "...", "timeStamp": "...", ...}
    """
    try:
        payment_service = PaymentService(db)

        # 创建微信支付订单
        order, payment_params = await payment_service.create_wechat_payment_order(
            tenant_id=tenant_id,
            plan_type=payment_data.plan_type,
            duration_months=payment_data.duration_months,
            payment_method=payment_method,
            subscription_type=payment_data.subscription_type,
            openid=openid,
            description=payment_data.description,
        )

        return {
            "success": True,
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": float(order.amount),
            "currency": order.currency,
            "payment_method": payment_method,
            "payment_params": payment_params,  # Native: {code_url}, JSAPI: {appId, timeStamp, ...}
            "expires_at": order.expired_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error creating wechat payment order: {e}")
        raise HTTPException(status_code=500, detail=f"创建微信支付订单失败: {str(e)}")


@router.post("/callback/wechat/notify", summary="微信支付异步回调")
async def wechat_notify_callback(
    request: Request,
    db: DBDep,
):
    """
    微信支付异步回调(服务器到服务器通知)

    **功能**:
    - 验证签名(必须)
    - 解密回调数据
    - 更新订单状态
    - 激活订阅

    **重要**:
    - 必须返回 {"code": "SUCCESS", "message": "成功"} 表示处理成功
    - 必须返回 {"code": "FAIL", "message": "失败原因"} 表示处理失败
    - 微信会重试多次

    **请求体**: 微信POST的加密JSON数据
    """
    try:
        # 获取请求头和请求体
        headers = dict(request.headers)
        body = await request.body()

        logger.info(f"Received wechat notify, serial: {headers.get('Wechatpay-Serial')}")

        # 处理异步通知
        payment_service = PaymentService(db)
        success = await payment_service.handle_wechat_notify(headers, body.decode())

        if success:
            logger.info("Wechat notify processed successfully")
            return {"code": "SUCCESS", "message": "成功"}
        else:
            logger.error("Wechat notify processing failed")
            return {"code": "FAIL", "message": "处理失败"}

    except Exception as e:
        logger.error(f"Error in wechat notify callback: {e}")
        return {"code": "FAIL", "message": str(e)}


@router.post("/wechat/orders/{order_number}/refund", summary="微信支付退款")
async def refund_wechat_order(
    order_number: str,
    refund_data: RefundRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    微信支付退款

    **路径参数**:
    - order_number: 订单编号

    **请求参数**:
    - refund_amount: 退款金额(不填则全额退款)
    - refund_reason: 退款原因

    **响应**:
    - refund_id: 微信退款单号
    - refund_status: 退款状态
    - refund_amount: 退款金额
    """
    try:
        payment_service = PaymentService(db)

        result = await payment_service.refund_wechat_order(
            order_number=order_number,
            refund_amount=refund_data.refund_amount,
            refund_reason=refund_data.refund_reason,
        )

        return {
            "refund_id": result.get("refund_id", ""),
            "refund_status": "success" if result["success"] else "failed",
            "refund_amount": result["refund_amount"],
            "refund_time": "",
            "message": result["message"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing wechat refund: {e}")
        raise HTTPException(status_code=500, detail=f"微信退款失败: {str(e)}")


# ===== 套餐订阅管理接口 =====

@router.post("/subscription/subscribe", response_model=SubscriptionResponse, summary="订阅套餐")
async def subscribe_plan(
    request_data: SubscribePlanRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    订阅套餐流程:
    1. 验证套餐有效性
    2. 计算价格
    3. 创建支付订单
    4. 返回支付信息

    **请求参数**:
    - plan_type: 套餐类型(basic/professional/enterprise)
    - duration_months: 订阅时长(1/3/6/12个月)
    - payment_method: 支付方式(alipay/wechat)
    - auto_renew: 是否自动续费

    **响应**:
    - success: 是否成功
    - message: 提示信息
    - order_number: 支付订单号
    - payment_required: 是否需要支付
    - payment_amount: 需支付金额
    """
    try:
        # 验证套餐类型
        valid_plans = ["basic", "professional", "enterprise"]
        if request_data.plan_type not in valid_plans:
            raise HTTPException(status_code=400, detail=f"无效的套餐类型: {request_data.plan_type}")

        # 计算订单金额
        payment_service = PaymentService(db)
        amount = payment_service.calculate_amount(
            plan_type=request_data.plan_type,
            duration_months=request_data.duration_months
        )

        # 创建支付订单
        payment_type = PaymentType.PC if request_data.payment_method == "alipay" else PaymentType.MOBILE

        order, payment_html = await payment_service.create_payment_order(
            tenant_id=tenant_id,
            plan_type=request_data.plan_type,
            duration_months=request_data.duration_months,
            payment_type=payment_type,
            subscription_type=SubscriptionType.NEW,
            description=f"订阅{request_data.plan_type}套餐 {request_data.duration_months}个月"
        )

        logger.info(
            f"Created subscription order: tenant={tenant_id}, "
            f"plan={request_data.plan_type}, order={order.order_number}"
        )

        return SubscriptionResponse(
            success=True,
            message="订单创建成功，请完成支付",
            order_number=order.order_number,
            payment_required=True,
            payment_amount=amount
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing plan: {e}")
        raise HTTPException(status_code=500, detail=f"订阅套餐失败: {str(e)}")


@router.put("/subscription/change", response_model=SubscriptionResponse, summary="变更套餐")
async def change_plan(
    request_data: ChangePlanRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    变更套餐(升级/降级):
    - 升级: 立即生效，计算差价并创建支付订单
    - 降级: 下个计费周期生效，不退款

    **请求参数**:
    - new_plan_type: 新套餐类型
    - effective_immediately: 是否立即生效(默认true)

    **响应**:
    - success: 是否成功
    - message: 提示信息
    - subscription: 订阅详情
    - order_number: 支付订单号(仅升级时)
    - payment_required: 是否需要支付
    - payment_amount: 需支付金额(仅升级时)
    """
    try:
        subscription_service = SubscriptionService(db)

        # 获取当前订阅
        subscription = await subscription_service.get_subscription(tenant_id)

        if subscription.plan_type == request_data.new_plan_type:
            raise HTTPException(status_code=400, detail="新套餐与当前套餐相同")

        # 判断是升级还是降级
        plan_levels = {"free": 0, "basic": 1, "professional": 2, "enterprise": 3}
        current_level = plan_levels.get(subscription.plan_type, 0)
        new_level = plan_levels.get(request_data.new_plan_type, 0)

        is_upgrade = new_level > current_level

        if is_upgrade and request_data.effective_immediately:
            # 升级: 计算差价并创建支付订单
            price_detail = await subscription_service.calculate_prorated_price(
                tenant_id=tenant_id,
                new_plan=request_data.new_plan_type
            )

            if price_detail["prorated_charge"] > 0:
                # 创建差价支付订单
                payment_service = PaymentService(db)
                from decimal import Decimal

                # 创建一个特殊的升级订单
                order, payment_html = await payment_service.create_payment_order(
                    tenant_id=tenant_id,
                    plan_type=request_data.new_plan_type,
                    duration_months=1,  # 使用1个月作为基数
                    payment_type=PaymentType.PC,
                    subscription_type=SubscriptionType.UPGRADE,
                    description=f"升级到{request_data.new_plan_type}套餐差价"
                )

                # 更新订单金额为实际差价
                order.amount = Decimal(str(price_detail["prorated_charge"]))
                await db.commit()

                return SubscriptionResponse(
                    success=True,
                    message=f"需要补差价 ¥{price_detail['prorated_charge']}，请完成支付",
                    order_number=order.order_number,
                    payment_required=True,
                    payment_amount=Decimal(str(price_detail["prorated_charge"]))
                )
            else:
                # 无需补差价，直接升级
                updated_subscription = await subscription_service.change_plan(
                    tenant_id=tenant_id,
                    new_plan=request_data.new_plan_type,
                    effective_date=None
                )

                return SubscriptionResponse(
                    success=True,
                    message="套餐升级成功",
                    payment_required=False
                )

        else:
            # 降级: 设置为下个周期生效
            effective_date = subscription.expire_at
            updated_subscription = await subscription_service.change_plan(
                tenant_id=tenant_id,
                new_plan=request_data.new_plan_type,
                effective_date=effective_date
            )

            return SubscriptionResponse(
                success=True,
                message=f"套餐将在 {effective_date.strftime('%Y-%m-%d')} 降级为 {request_data.new_plan_type}",
                payment_required=False
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing plan: {e}")
        raise HTTPException(status_code=500, detail=f"变更套餐失败: {str(e)}")


@router.get("/subscription", response_model=SubscriptionDetail, summary="获取订阅详情")
async def get_subscription(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    获取当前订阅详情

    **响应**:
    - subscription_id: 订阅ID
    - tenant_id: 租户ID
    - plan_type: 套餐类型
    - status: 订阅状态
    - start_date: 开始日期
    - expire_at: 到期日期
    - auto_renew: 是否自动续费
    - conversation_quota: 对话配额
    - api_quota: API配额
    - storage_quota: 存储配额
    - concurrent_quota: 并发配额
    - enabled_features: 已启用功能列表
    - pending_plan: 待变更套餐(如有)
    """
    try:
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_subscription(tenant_id)

        # 解析 enabled_features (可能是JSON字符串)
        import json
        features = subscription.enabled_features
        if isinstance(features, str):
            features = json.loads(features)

        return SubscriptionDetail(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_type=subscription.plan_type,
            status=subscription.status,
            start_date=subscription.start_date,
            expire_at=subscription.expire_at,
            auto_renew=subscription.auto_renew,
            is_trial=subscription.is_trial,
            conversation_quota=subscription.conversation_quota,
            api_quota=subscription.api_quota,
            storage_quota=subscription.storage_quota,
            concurrent_quota=subscription.concurrent_quota,
            enabled_features=features,
            pending_plan=subscription.pending_plan,
            plan_change_date=subscription.plan_change_date,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail=f"获取订阅详情失败: {str(e)}")


@router.post("/subscription/cancel-renewal", summary="取消自动续费")
async def cancel_auto_renewal(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    取消自动续费

    **功能**:
    - 将auto_renew设置为False
    - 不影响当前订阅周期

    **响应**:
    - success: 是否成功
    - message: 提示信息
    """
    try:
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.get_subscription(tenant_id)

        if not subscription.auto_renew:
            return {
                "success": True,
                "message": "当前未开启自动续费"
            }

        subscription.auto_renew = False
        await db.commit()

        logger.info(f"Cancelled auto renewal: tenant={tenant_id}")

        return {
            "success": True,
            "message": "已取消自动续费，当前订阅周期不受影响"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling auto renewal: {e}")
        raise HTTPException(status_code=500, detail=f"取消自动续费失败: {str(e)}")


@router.get("/subscription/prorated-price", response_model=ProratedPriceDetail, summary="计算升级差价")
async def get_prorated_price(
    new_plan_type: str = Query(..., description="新套餐类型"),
    tenant_id: TenantDep = None,
    db: DBDep = None,
):
    """
    计算升级到新套餐需要补的差价

    **查询参数**:
    - new_plan_type: 新套餐类型(basic/professional/enterprise)

    **响应**:
    - current_plan: 当前套餐
    - new_plan: 新套餐
    - current_plan_value: 当前套餐剩余价值
    - new_plan_value: 新套餐剩余价值
    - prorated_charge: 需补差价
    - remaining_days: 剩余天数
    """
    try:
        subscription_service = SubscriptionService(db)
        price_detail = await subscription_service.calculate_prorated_price(
            tenant_id=tenant_id,
            new_plan=new_plan_type
        )

        from decimal import Decimal
        return ProratedPriceDetail(
            current_plan=price_detail["current_plan"],
            new_plan=price_detail["new_plan"],
            current_plan_value=Decimal(str(price_detail["current_plan_value"])),
            new_plan_value=Decimal(str(price_detail["new_plan_value"])),
            prorated_charge=Decimal(str(price_detail["prorated_charge"])),
            remaining_days=price_detail["remaining_days"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating prorated price: {e}")
        raise HTTPException(status_code=500, detail=f"计算差价失败: {str(e)}")
