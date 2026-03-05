"""
支付相关数据模型

包含：
- PaymentOrder: 支付订单表
- PaymentTransaction: 支付交易记录表  
- PaymentChannelConfig: 支付渠道配置表
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    FAILED = "failed"  # 支付失败
    CANCELLED = "cancelled"  # 已取消
    REFUNDING = "refunding"  # 退款中
    REFUNDED = "refunded"  # 已退款
    EXPIRED = "expired"  # 已过期


class PaymentChannel(str, Enum):
    """支付渠道"""
    ALIPAY = "alipay"  # 支付宝
    WECHAT = "wechat"  # 微信支付


class PaymentType(str, Enum):
    """支付类型"""
    PC = "pc"  # PC 网站支付
    MOBILE = "mobile"  # 手机网站支付
    APP = "app"  # APP 支付（预留）
    NATIVE = "native"  # 扫码支付


class SubscriptionType(str, Enum):
    """订阅类型"""
    NEW = "new"  # 新订阅
    RENEWAL = "renewal"  # 续费
    UPGRADE = "upgrade"  # 升级


class TransactionType(str, Enum):
    """交易类型"""
    PAYMENT = "payment"  # 支付
    REFUND = "refund"  # 退款


class TransactionStatus(str, Enum):
    """交易状态"""
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    PENDING = "pending"  # 处理中


class PaymentOrder(BaseModel):
    """支付订单表"""
    __tablename__ = "payment_orders"

    # 订单信息
    order_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="订单编号"
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    
    # 支付信息
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="订单金额（元）"
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="CNY", nullable=False, comment="货币类型"
    )
    payment_channel: Mapped[PaymentChannel] = mapped_column(
        SQLEnum(PaymentChannel), nullable=False, comment="支付渠道"
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        SQLEnum(PaymentType), nullable=False, comment="支付类型"
    )
    
    # 订单状态
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True, comment="订单状态"
    )
    
    # 订阅信息
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        SQLEnum(SubscriptionType), nullable=False, comment="订阅类型"
    )
    plan_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="套餐类型"
    )
    duration_months: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="订阅时长（月）"
    )
    
    # 第三方支付信息
    trade_no: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, comment="第三方交易号"
    )
    payment_url: Mapped[str | None] = mapped_column(
        Text, comment="支付URL或表单HTML"
    )
    qr_code_url: Mapped[str | None] = mapped_column(
        Text, comment="二维码URL，用于前端展示"
    )
    
    # 时间信息
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, comment="支付时间")
    expired_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="订单过期时间"
    )
    
    # 回调信息
    callback_data: Mapped[str | None] = mapped_column(Text, comment="回调数据（JSON）")
    callback_count: Mapped[int] = mapped_column(Integer, default=0, comment="回调次数")
    
    # 备注
    description: Mapped[str | None] = mapped_column(String(500), comment="订单描述")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    
    # 关系
    tenant = relationship("Tenant", back_populates="payment_orders")
    transactions = relationship("PaymentTransaction", back_populates="order", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_payment_orders_tenant_status', 'tenant_id', 'status'),
        Index('idx_order_created_at', 'created_at'),
        {'comment': '支付订单表'}
    )

    def __repr__(self):
        return f"<PaymentOrder(order_number={self.order_number}, status={self.status}, amount={self.amount})>"


class PaymentTransaction(BaseModel):
    """支付交易记录表"""
    __tablename__ = "payment_transactions"

    # 关联订单
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("payment_orders.id"), nullable=False, index=True, comment="订单ID"
    )
    
    # 交易信息
    transaction_no: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True, comment="交易流水号"
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False, comment="交易类型"
    )
    transaction_status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus), nullable=False, comment="交易状态"
    )
    
    # 金额信息
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="交易金额（元）"
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="CNY", nullable=False, comment="货币类型"
    )
    
    # 第三方信息
    third_party_trade_no: Mapped[str | None] = mapped_column(
        String(128), index=True, comment="第三方交易号"
    )
    payment_channel: Mapped[PaymentChannel] = mapped_column(
        SQLEnum(PaymentChannel), nullable=False, comment="支付渠道"
    )
    
    # 交易详情
    transaction_data: Mapped[str | None] = mapped_column(Text, comment="交易数据（JSON）")
    error_code: Mapped[str | None] = mapped_column(String(50), comment="错误代码")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    
    # 时间信息
    transaction_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="交易时间"
    )
    
    # 备注
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    
    # 关系
    order = relationship("PaymentOrder", back_populates="transactions")
    
    # 索引
    __table_args__ = (
        Index('idx_order_type', 'order_id', 'transaction_type'),
        Index('idx_txn_time', 'transaction_time'),
        {'comment': '支付交易记录表'}
    )

    def __repr__(self):
        return f"<PaymentTransaction(transaction_no={self.transaction_no}, type={self.transaction_type}, status={self.transaction_status})>"


class PaymentChannelConfig(BaseModel):
    """支付渠道配置表"""
    __tablename__ = "payment_channel_configs"

    # 渠道信息
    channel: Mapped[PaymentChannel] = mapped_column(
        SQLEnum(PaymentChannel), unique=True, nullable=False, comment="支付渠道"
    )
    channel_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="渠道名称"
    )
    
    # 配置信息（敏感信息应加密存储或使用环境变量）
    app_id: Mapped[str | None] = mapped_column(String(128), comment="应用ID")
    is_sandbox: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否沙箱环境"
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    
    # 费率配置
    fee_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=0.006, comment="手续费率"
    )
    
    # 备注
    description: Mapped[str | None] = mapped_column(Text, comment="渠道描述")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    
    __table_args__ = (
        {'comment': '支付渠道配置表'}
    )

    def __repr__(self):
        return f"<PaymentChannelConfig(channel={self.channel}, is_active={self.is_active})>"
