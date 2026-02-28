"""电商平台适配器抽象基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


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


class BasePlatformAdapter(ABC):
    """电商平台适配器抽象基类

    所有电商平台（拼多多、淘宝、京东等）的适配器都继承此类，
    实现统一的商品/订单操作接口。
    """

    def __init__(self, app_key: str, app_secret: str, access_token: str | None = None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token

    @abstractmethod
    async def fetch_products(self, page: int = 1, page_size: int = 50) -> PageResult:
        """分页拉取商品列表"""
        ...

    @abstractmethod
    async def fetch_product_detail(self, product_id: str) -> ProductDTO:
        """获取商品详情"""
        ...

    @abstractmethod
    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        """拉取指定时间后变更的商品"""
        ...

    @abstractmethod
    async def upload_image(self, product_id: str, image_url: str) -> str:
        """上传图片到平台，返回平台侧图片URL"""
        ...

    @abstractmethod
    async def upload_video(self, product_id: str, video_url: str) -> str:
        """上传视频到平台，返回平台侧视频URL"""
        ...

    @abstractmethod
    async def update_product(self, product_id: str, data: dict) -> bool:
        """更新商品信息"""
        ...

    @abstractmethod
    async def fetch_orders(
        self,
        page: int = 1,
        page_size: int = 50,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
    ) -> PageResult:
        """分页拉取订单列表"""
        ...

    @abstractmethod
    async def fetch_order_detail(self, order_id: str) -> OrderDTO:
        """获取订单详情"""
        ...
