"""
租户表模型
"""
from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel


class Tenant(BaseModel):
    """租户表"""

    __tablename__ = "tenants"
    __table_args__ = (
        Index("idx_tenant_id", "tenant_id", unique=True),
        Index("idx_tenant_email", "contact_email"),
        Index("idx_tenants_status", "status"),
        Index("idx_tenant_plan", "current_plan"),
        Index("idx_tenant_api_key_prefix", "api_key_prefix"),  # API Key前缀索引，用于快速查找
        {"comment": "租户表"},
    )

    # 基本信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="租户唯一标识"
    )
    company_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="公司名称")
    contact_name: Mapped[str | None] = mapped_column(String(128), comment="联系人姓名")
    contact_email: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="联系邮箱"
    )
    contact_phone: Mapped[str | None] = mapped_column(String(20), comment="联系电话")

    # 认证信息
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希(用于登录)"
    )
    api_key_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="API密钥(加密存储)"
    )
    api_key_prefix: Mapped[str | None] = mapped_column(
        String(16), comment="API密钥前缀(用于快速查找)"
    )
    api_key_salt: Mapped[str | None] = mapped_column(String(64), comment="API密钥盐值")

    # 密码认证信息
    login_attempts: Mapped[int] = mapped_column(Integer, default=0, comment="登录失败次数")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, comment="锁定截止时间")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后登录时间")
    last_login_ip: Mapped[str | None] = mapped_column(String(64), comment="最后登录IP")

    # Refresh Token
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(255), comment="刷新Token哈希"
    )

    # 状态信息
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        comment="状态(active/suspended/deleted)",
    )
    current_plan: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="free",
        comment="当前套餐(free/basic/professional/enterprise)",
    )
    plan_expire_at: Mapped[datetime | None] = mapped_column(DateTime, comment="套餐过期时间")

    # 配置信息
    config: Mapped[dict | None] = mapped_column(
        Text, comment="租户配置(JSON格式: Logo、主题色、品牌名称等)"
    )

    # 统计信息
    total_conversations: Mapped[int] = mapped_column(
        Integer, default=0, comment="总对话次数"
    )
    total_messages: Mapped[int] = mapped_column(Integer, default=0, comment="总消息数")
    total_spent: Mapped[float] = mapped_column(Float, default=0.0, comment="总消费金额")

    # 最后活跃时间
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后活跃时间")

    # 备注
    remarks: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 关联关系
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="tenant", lazy="selectin"
    )
    payment_orders: Mapped[list["PaymentOrder"]] = relationship(
        "PaymentOrder", back_populates="tenant", lazy="select"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="tenant", lazy="select"
    )
    bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="tenant", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.company_name} ({self.current_plan})>"


class Subscription(BaseModel):
    """套餐订阅表"""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("idx_subscription_tenant", "tenant_id"),
        Index("idx_subscription_status", "status"),
        {"comment": "套餐订阅表"},
    )

    # 订阅唯一标识
    subscription_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), comment="订阅唯一标识(UUID)"
    )

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, comment="租户ID", index=True
    )

    # 套餐信息
    plan_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="套餐类型(free/basic/professional/enterprise)",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        comment="状态(active/expired/cancelled)",
    )

    # 功能模块
    enabled_features: Mapped[list] = mapped_column(
        Text, nullable=False, comment='开通的功能模块(JSON数组，如 ["BASIC_CHAT", "ORDER_QUERY"])'
    )
    feature_config: Mapped[dict | None] = mapped_column(
        Text, comment="功能模块配置(JSON对象)"
    )

    # 配额
    conversation_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="对话次数配额"
    )
    concurrent_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="并发会话配额"
    )
    storage_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="存储空间配额(GB)"
    )
    api_quota: Mapped[int] = mapped_column(Integer, nullable=False, comment="API调用配额")

    # 时间
    start_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="订阅开始时间"
    )
    expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")

    # 续费设置
    auto_renew: Mapped[bool] = mapped_column(nullable=False, default=False, comment="是否自动续费")
    is_trial: Mapped[bool] = mapped_column(nullable=False, default=False, comment="是否试用")

    # 待生效套餐（用于延期生效）
    pending_plan: Mapped[str | None] = mapped_column(String(32), comment="待生效套餐")
    plan_change_date: Mapped[datetime | None] = mapped_column(DateTime, comment="套餐变更生效日期")

    # 关联关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription {self.tenant_id} - {self.plan_type}>"


class UsageRecord(BaseModel):
    """用量记录表"""

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("idx_usage_tenant_date", "tenant_id", "record_date"),
        {"comment": "用量记录表"},
    )

    # 订阅唯一标识
    subscription_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), comment="订阅唯一标识(UUID)"
    )

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, comment="租户ID", index=True
    )
    record_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="记录日期", index=True
    )

    # 用量统计
    conversation_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="对话次数"
    )
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输入Token数")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输出Token数")
    storage_used: Mapped[float] = mapped_column(Float, default=0.0, comment="存储使用(GB)")
    api_calls: Mapped[int] = mapped_column(Integer, default=0, comment="API调用次数")

    # 费用（超出套餐部分）
    overage_fee: Mapped[float] = mapped_column(
        Float, default=0.0, comment="超额费用"
    )

    # 关联关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="usage_records")

    def __repr__(self) -> str:
        return f"<UsageRecord {self.tenant_id} - {self.record_date}>"


class Bill(BaseModel):
    """账单表"""

    __tablename__ = "bills"
    __table_args__ = (
        Index("idx_bill_tenant", "tenant_id"),
        Index("idx_bill_period", "billing_period"),
        Index("idx_bill_status", "status"),
        {"comment": "账单表"},
    )

    # 账单信息
    bill_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="账单ID"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, comment="租户ID", index=True
    )
    billing_period: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="账期(格式: 2024-01)"
    )

    # 费用明细
    base_fee: Mapped[float] = mapped_column(Float, default=0.0, comment="基础套餐费")
    overage_fee: Mapped[float] = mapped_column(Float, default=0.0, comment="超额费用")
    discount: Mapped[float] = mapped_column(Float, default=0.0, comment="折扣")
    adjustment_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="调整金额")
    adjustment_reason: Mapped[str | None] = mapped_column(Text, comment="调整原因")
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, comment="总金额")

    # 支付信息
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="状态(pending/paid/overdue/cancelled)",
    )
    payment_method: Mapped[str | None] = mapped_column(
        String(32), comment="支付方式(alipay/wechat/bank_transfer等)"
    )
    payment_time: Mapped[datetime | None] = mapped_column(DateTime, comment="支付时间")
    transaction_id: Mapped[str | None] = mapped_column(String(128), comment="交易流水号")

    # 发票信息
    invoice_issued: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="是否已开发票"
    )
    invoice_number: Mapped[str | None] = mapped_column(String(64), comment="发票号")

    # 到期时间
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="应付日期")

    # 退款信息
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0, comment="退款金额")
    refund_reason: Mapped[str | None] = mapped_column(Text, comment="退款原因")

    # 关联关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="bills")

    def __repr__(self) -> str:
        return f"<Bill {self.bill_id} - {self.billing_period} - {self.total_amount}>"
