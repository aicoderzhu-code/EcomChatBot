"""
支付 API 路由

提供支付相关的HTTP接口
"""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_tenant
from db.session import get_db
from models.payment import PaymentType, SubscriptionType
from models.tenant import Tenant
from schemas.payment import (
    CreatePaymentResponse,
    PaymentOrderCreate,
    PaymentOrderDetail,
    RefundRequest,
    RefundResponse,
)
from services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["支付管理"])


@router.post("/orders/create", response_model=CreatePaymentResponse, summary="创建支付订单")
async def create_payment_order(
    payment_data: PaymentOrderCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
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
            tenant_id=current_tenant.id,
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
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
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
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
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
