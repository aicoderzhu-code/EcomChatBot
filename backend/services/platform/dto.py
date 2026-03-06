"""平台对接统一 DTO 和事件模型"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ===== 枚举 =====

class PlatformType(str, Enum):
    """支持的电商平台"""
    PINDUODUO = "pinduoduo"
    DOUYIN = "douyin"
    TAOBAO = "taobao"
    JD = "jd"
    KUAISHOU = "kuaishou"


class EventType(str, Enum):
    """平台事件类型"""
    MESSAGE = "message"
    ORDER_STATUS = "order_status"
    AFTERSALE = "aftersale"
    PRODUCT_CHANGE = "product_change"


class AfterSaleType(str, Enum):
    """售后类型"""
    REFUND_ONLY = "refund_only"
    RETURN_REFUND = "return_refund"
    EXCHANGE = "exchange"


class AfterSaleStatus(str, Enum):
    """售后状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AuthorizationStatus(str, Enum):
    """授权状态"""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ===== 已有 DTO（从 base_adapter.py 迁移） =====

@dataclass
class ProductDTO:
    """商品数据传输对象"""
    platform_product_id: str
    title: str
    price: float
    original_price: float | None = None
    description: str | None = None
    category: str | None = None
    images: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    attributes: dict | None = None
    sales_count: int = 0
    stock: int = 0
    status: str = "active"
    platform_data: dict | None = None


@dataclass
class OrderDTO:
    """订单数据传输对象"""
    platform_order_id: str
    product_id: str | None = None
    product_title: str = ""
    buyer_id: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    total_amount: float = 0.0
    status: str = "pending"
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    completed_at: datetime | None = None
    refund_amount: float | None = None
    platform_data: dict | None = None


@dataclass
class PageResult:
    """分页结果"""
    items: list
    total: int
    page: int
    page_size: int


# ===== 新增 DTO =====

@dataclass
class TokenResult:
    """OAuth Token 换取结果"""
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 7200
    shop_id: str | None = None
    shop_name: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class AfterSaleDTO:
    """售后数据传输对象"""
    platform_aftersale_id: str
    order_id: str
    aftersale_type: str = "refund_only"
    status: str = "pending"
    reason: str = ""
    refund_amount: float = 0.0
    buyer_id: str = ""
    platform_data: dict | None = None


# ===== 事件模型 =====

@dataclass
class PlatformEvent:
    """标准化平台事件基类"""
    event_type: str
    platform_type: str
    shop_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_data: dict = field(default_factory=dict)
    event_id: str = ""


@dataclass
class MessageEvent(PlatformEvent):
    """消息事件"""
    buyer_id: str = ""
    conversation_id: str = ""
    content: str = ""
    msg_type: str = "text"


@dataclass
class OrderEvent(PlatformEvent):
    """订单状态变更事件"""
    order_id: str = ""
    old_status: str = ""
    new_status: str = ""


@dataclass
class AfterSaleEvent(PlatformEvent):
    """售后事件"""
    aftersale_id: str = ""
    order_id: str = ""
    aftersale_type: str = ""
    status: str = ""
