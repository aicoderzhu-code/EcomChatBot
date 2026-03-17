"""
支付相关 Pydantic schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from models.payment import (
    OrderStatus,
    PaymentChannel,
    PaymentType,
    SubscriptionType,
    TransactionType,
    TransactionStatus,
)


# ========== 支付订单 Schemas ==========

class PaymentOrderCreate(BaseModel):
    """创建支付订单"""
    plan_type: str = Field(..., description="套餐类型：monthly/quarterly/semi_annual/annual 或加量包：image_addon/video_addon")
    duration_months: int = Field(..., ge=1, le=36, description="订阅时长（月）：1-36")
    payment_type: PaymentType = Field(default=PaymentType.PC, description="支付类型：pc/mobile")
    subscription_type: SubscriptionType = Field(default=SubscriptionType.NEW, description="订阅类型")
    description: Optional[str] = Field(None, max_length=500, description="订单描述")


class PaymentOrderResponse(BaseModel):
    """支付订单响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    tenant_id: int
    amount: Decimal
    currency: str
    payment_channel: PaymentChannel
    payment_type: PaymentType
    status: OrderStatus
    subscription_type: SubscriptionType
    plan_type: str
    duration_months: int
    trade_no: Optional[str] = None
    payment_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    expired_at: datetime
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentOrderDetail(PaymentOrderResponse):
    """支付订单详情"""
    callback_count: int
    remark: Optional[str] = None


class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    order_id: int
    order_number: str
    amount: Decimal
    currency: str
    payment_html: str = Field(..., description="支付表单HTML（自动提交）")
    expires_at: datetime = Field(..., description="订单过期时间")


# ========== 支付交易 Schemas ==========

class PaymentTransactionResponse(BaseModel):
    """支付交易响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    transaction_no: str
    transaction_type: TransactionType
    transaction_status: TransactionStatus
    amount: Decimal
    currency: str
    third_party_trade_no: Optional[str] = None
    payment_channel: PaymentChannel
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    transaction_time: datetime
    created_at: datetime


# ========== 回调相关 Schemas ==========

class AlipayReturnParams(BaseModel):
    """支付宝同步回调参数"""
    out_trade_no: str = Field(..., description="商户订单号")
    trade_no: str = Field(..., description="支付宝交易号")
    total_amount: str = Field(..., description="订单金额")
    seller_id: str = Field(..., description="卖家支付宝用户ID")
    timestamp: str = Field(..., description="时间戳")
    sign: str = Field(..., description="签名")
    sign_type: str = Field(..., description="签名类型")


class AlipayNotifyParams(BaseModel):
    """支付宝异步回调参数"""
    notify_time: str = Field(..., description="通知时间")
    notify_type: str = Field(..., description="通知类型")
    notify_id: str = Field(..., description="通知校验ID")
    app_id: str = Field(..., description="应用ID")
    out_trade_no: str = Field(..., description="商户订单号")
    trade_no: str = Field(..., description="支付宝交易号")
    trade_status: str = Field(..., description="交易状态")
    total_amount: str = Field(..., description="订单金额")
    receipt_amount: str = Field(..., description="实收金额")
    buyer_id: str = Field(..., description="买家支付宝用户ID")
    seller_id: str = Field(..., description="卖家支付宝用户ID")
    gmt_create: str = Field(..., description="交易创建时间")
    gmt_payment: str = Field(..., description="交易付款时间")
    sign: str = Field(..., description="签名")
    sign_type: str = Field(..., description="签名类型")


# ========== 查询相关 Schemas ==========

class OrderQueryParams(BaseModel):
    """订单查询参数"""
    status: Optional[OrderStatus] = None
    payment_channel: Optional[PaymentChannel] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class OrderListResponse(BaseModel):
    """订单列表响应"""
    total: int
    page: int
    page_size: int
    items: list[PaymentOrderResponse]


# ========== 退款相关 Schemas ==========

class RefundRequest(BaseModel):
    """退款请求"""
    refund_amount: Optional[Decimal] = Field(None, description="退款金额（元），不填则全额退款")
    refund_reason: str = Field(..., max_length=200, description="退款原因")


class RefundResponse(BaseModel):
    """退款响应"""
    refund_id: int
    refund_status: TransactionStatus
    refund_amount: Decimal
    refund_time: datetime
    message: str


# ========== 支付渠道配置 Schemas ==========

class PaymentChannelConfigResponse(BaseModel):
    """支付渠道配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: PaymentChannel
    channel_name: str
    is_active: bool
    fee_rate: Decimal
    description: Optional[str] = None
