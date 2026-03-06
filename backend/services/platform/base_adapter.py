"""电商平台适配器抽象基类"""
from abc import ABC, abstractmethod
from datetime import datetime

from services.platform.dto import (
    ProductDTO, OrderDTO, PageResult, TokenResult, AfterSaleDTO,
    PlatformEvent,
)


class BasePlatformAdapter(ABC):
    """电商平台适配器抽象基类

    所有电商平台（拼多多、淘宝、京东等）的适配器都继承此类，
    实现统一的 OAuth + 消息 + 商品 + 订单 + 售后 接口。
    """

    def __init__(self, app_key: str, app_secret: str, access_token: str | None = None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token

    # ===== OAuth 授权 =====

    @abstractmethod
    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        """生成平台 OAuth 授权跳转 URL"""
        ...

    @abstractmethod
    async def exchange_token(self, code: str) -> TokenResult:
        """用授权码换取 access_token"""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenResult:
        """刷新 access_token"""
        ...

    # ===== 消息收发 =====

    @abstractmethod
    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """验证 Webhook 签名"""
        ...

    @abstractmethod
    def parse_webhook_event(self, body: dict) -> list[PlatformEvent]:
        """解析 Webhook 载荷为标准事件列表"""
        ...

    @abstractmethod
    async def send_message(
        self, conversation_id: str, content: str, msg_type: str = "text"
    ) -> bool:
        """向买家发送消息"""
        ...

    # ===== 商品 =====

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

    # ===== 订单 =====

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

    # ===== 售后 =====

    @abstractmethod
    async def fetch_aftersales(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> PageResult:
        """分页拉取售后列表"""
        ...

    @abstractmethod
    async def get_aftersale_detail(self, aftersale_id: str) -> AfterSaleDTO:
        """获取售后详情"""
        ...

    @abstractmethod
    async def approve_refund(self, aftersale_id: str) -> bool:
        """同意退款"""
        ...

    @abstractmethod
    async def reject_refund(self, aftersale_id: str, reason: str) -> bool:
        """拒绝退款"""
        ...
