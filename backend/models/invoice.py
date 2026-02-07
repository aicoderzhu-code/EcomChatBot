"""
发票相关数据模型
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel


class InvoiceType(str, Enum):
    """发票类型"""
    NORMAL = "normal"  # 普通发票
    VAT_SPECIAL = "vat_special"  # 增值税专用发票
    ELECTRONIC = "electronic"  # 电子发票


class InvoiceStatus(str, Enum):
    """发票状态"""
    PENDING = "pending"  # 待开票
    ISSUED = "issued"  # 已开票
    SENT = "sent"  # 已发送
    CANCELLED = "cancelled"  # 已作废
    REJECTED = "rejected"  # 已拒绝


class Invoice(BaseModel):
    """发票表"""
    __tablename__ = "invoices"

    # 发票基本信息
    invoice_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="发票号码"
    )
    invoice_code: Mapped[Optional[str]] = mapped_column(
        String(32), comment="发票代码"
    )

    # 关联信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True, comment="租户ID"
    )
    bill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bills.id"), comment="关联账单ID"
    )

    # 发票类型和状态
    invoice_type: Mapped[InvoiceType] = mapped_column(
        SQLEnum(InvoiceType), default=InvoiceType.ELECTRONIC, nullable=False, comment="发票类型"
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False, index=True, comment="发票状态"
    )

    # 金额信息
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="发票金额(含税)"
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), comment="税额"
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.06"), comment="税率(默认6%)"
    )

    # 购买方信息
    buyer_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="购买方名称"
    )
    buyer_tax_number: Mapped[Optional[str]] = mapped_column(
        String(64), comment="购买方税号"
    )
    buyer_address: Mapped[Optional[str]] = mapped_column(
        String(512), comment="购买方地址电话"
    )
    buyer_bank_account: Mapped[Optional[str]] = mapped_column(
        String(256), comment="购买方开户行及账号"
    )

    # 销售方信息(从配置读取)
    seller_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="销售方名称"
    )
    seller_tax_number: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="销售方税号"
    )

    # 发票内容
    item_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="项目名称"
    )
    item_specification: Mapped[Optional[str]] = mapped_column(
        String(256), comment="规格型号"
    )
    item_unit: Mapped[str] = mapped_column(
        String(32), default="项", comment="单位"
    )
    item_quantity: Mapped[int] = mapped_column(
        Integer, default=1, comment="数量"
    )
    item_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="单价"
    )

    # 备注
    remark: Mapped[Optional[str]] = mapped_column(
        Text, comment="发票备注"
    )

    # 开票信息
    issued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="开票时间"
    )
    issued_by: Mapped[Optional[str]] = mapped_column(
        String(64), comment="开票人"
    )

    # 发送信息
    recipient_email: Mapped[Optional[str]] = mapped_column(
        String(128), comment="接收邮箱"
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="发送时间"
    )

    # PDF文件路径
    pdf_path: Mapped[Optional[str]] = mapped_column(
        String(512), comment="PDF文件路径"
    )

    # 作废信息
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="作废时间"
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(
        Text, comment="作废原因"
    )

    # 索引
    __table_args__ = (
        Index('idx_invoice_tenant_status', 'tenant_id', 'status'),
        Index('idx_invoice_issued_at', 'issued_at'),
        {'comment': '发票表'}
    )

    def __repr__(self):
        return f"<Invoice(invoice_number={self.invoice_number}, status={self.status}, amount={self.amount})>"


class InvoiceTitle(BaseModel):
    """发票抬头表(租户可以保存多个发票抬头)"""
    __tablename__ = "invoice_titles"

    # 租户信息
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True, comment="租户ID"
    )

    # 抬头信息
    title_name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="发票抬头名称"
    )
    tax_number: Mapped[Optional[str]] = mapped_column(
        String(64), comment="税号"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(512), comment="地址电话"
    )
    bank_account: Mapped[Optional[str]] = mapped_column(
        String(256), comment="开户行及账号"
    )

    # 发票类型
    invoice_type: Mapped[InvoiceType] = mapped_column(
        SQLEnum(InvoiceType), default=InvoiceType.ELECTRONIC, nullable=False, comment="发票类型"
    )

    # 是否默认
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否默认抬头"
    )

    # 索引
    __table_args__ = (
        Index('idx_invoice_title_tenant', 'tenant_id'),
        {'comment': '发票抬头表'}
    )

    def __repr__(self):
        return f"<InvoiceTitle(title_name={self.title_name}, tenant_id={self.tenant_id})>"
