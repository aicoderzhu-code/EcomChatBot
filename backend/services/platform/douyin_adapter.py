"""抖音抖店平台适配器"""
import logging
from datetime import datetime

from services.platform.base_adapter import (
    BasePlatformAdapter, OrderDTO, PageResult, ProductDTO,
)
from services.platform.douyin_client import DouyinClient

logger = logging.getLogger(__name__)


class DouyinAdapter(BasePlatformAdapter):
    """抖音抖店平台适配器"""

    def __init__(self, app_key: str, app_secret: str, access_token: str | None = None):
        super().__init__(app_key, app_secret, access_token)
        self.client = DouyinClient(app_key, app_secret)

    def _parse_product(self, raw: dict) -> ProductDTO:
        """将抖音商品原始数据转为 ProductDTO"""
        images = raw.get("pic", [])
        if isinstance(images, str):
            images = [images]

        return ProductDTO(
            platform_product_id=str(raw.get("product_id", "")),
            title=raw.get("name", ""),
            price=float(raw.get("price", 0)) / 100,  # 抖音价格单位为分
            original_price=float(raw.get("market_price", 0)) / 100 if raw.get("market_price") else None,
            description=raw.get("description", ""),
            category=raw.get("category_name", ""),
            images=images,
            videos=raw.get("video", []),
            attributes=raw.get("spec_list"),
            sales_count=raw.get("sales", 0),
            stock=raw.get("stock_num", 0),
            status="active" if raw.get("status") == 1 else "inactive",
            platform_data=raw,
        )

    async def fetch_products(self, page: int = 1, page_size: int = 50) -> PageResult:
        """拉取抖音商品列表"""
        result = await self.client.call_api(
            endpoint="/product/list",
            params={
                "page": page,
                "size": page_size,
            },
            access_token=self.access_token,
        )

        product_list = result.get("list", [])
        total = result.get("total", 0)

        products = [self._parse_product(p) for p in product_list]

        return PageResult(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def fetch_product_detail(self, product_id: str) -> ProductDTO:
        """获取抖音商品详情"""
        result = await self.client.call_api(
            endpoint="/product/detail",
            params={"product_id": product_id},
            access_token=self.access_token,
        )
        product_info = result.get("product", {})
        return self._parse_product(product_info)

    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        """拉取指定时间后变更的商品"""
        timestamp = int(since.timestamp())
        result = await self.client.call_api(
            endpoint="/product/list",
            params={
                "page": 1,
                "size": 100,
                "update_time_start": timestamp,
            },
            access_token=self.access_token,
        )
        product_list = result.get("list", [])
        return [self._parse_product(p) for p in product_list]

    async def upload_image(self, product_id: str, image_url: str) -> str:
        """上传图片到抖音"""
        result = await self.client.call_api(
            endpoint="/material/upload_image_by_url",
            params={"url": image_url},
            access_token=self.access_token,
        )
        return result.get("url", "")

    async def upload_video(self, product_id: str, video_url: str) -> str:
        """上传视频到抖音"""
        result = await self.client.call_api(
            endpoint="/material/upload_video_by_url",
            params={"url": video_url},
            access_token=self.access_token,
        )
        return result.get("video_id", "")

    async def update_product(self, product_id: str, data: dict) -> bool:
        """更新抖音商品信息"""
        params = {"product_id": product_id, **data}
        try:
            await self.client.call_api(
                endpoint="/product/edit",
                params=params,
                access_token=self.access_token,
            )
            return True
        except Exception as e:
            logger.error(f"更新商品失败: {e}")
            return False

    async def fetch_orders(
        self,
        page: int = 1,
        page_size: int = 50,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
    ) -> PageResult:
        """拉取抖音订单列表"""
        params: dict = {
            "page": page,
            "size": page_size,
        }
        if start_time:
            params["start_time"] = int(start_time.timestamp())
        if end_time:
            params["end_time"] = int(end_time.timestamp())
        if status:
            # 抖音订单状态映射
            status_map = {
                "pending": 1,
                "paid": 2,
                "shipped": 3,
                "completed": 4,
            }
            if status in status_map:
                params["order_status"] = status_map[status]

        result = await self.client.call_api(
            endpoint="/order/list",
            params=params,
            access_token=self.access_token,
        )

        order_list = result.get("list", [])
        total = result.get("total", 0)

        orders = [self._parse_order(o) for o in order_list]

        return PageResult(items=orders, total=total, page=page, page_size=page_size)

    def _parse_order(self, raw: dict) -> OrderDTO:
        """将抖音订单原始数据转为 OrderDTO"""
        return OrderDTO(
            platform_order_id=str(raw.get("order_id", "")),
            product_id=str(raw.get("product_id", "")),
            product_title=raw.get("product_name", ""),
            buyer_id=str(raw.get("buyer_id", "")),
            quantity=raw.get("item_num", 1),
            unit_price=float(raw.get("price", 0)) / 100,
            total_amount=float(raw.get("pay_amount", 0)) / 100,
            status=self._map_order_status(raw.get("order_status", 0)),
            paid_at=datetime.fromtimestamp(raw["pay_time"]) if raw.get("pay_time") else None,
            shipped_at=datetime.fromtimestamp(raw["ship_time"]) if raw.get("ship_time") else None,
            platform_data=raw,
        )

    @staticmethod
    def _map_order_status(douyin_status: int) -> str:
        """抖音订单状态映射"""
        status_map = {
            1: "pending",
            2: "paid",
            3: "shipped",
            4: "completed",
            5: "refunded",
            6: "cancelled",
        }
        return status_map.get(douyin_status, "pending")

    async def fetch_order_detail(self, order_id: str) -> OrderDTO:
        """获取抖音订单详情"""
        result = await self.client.call_api(
            endpoint="/order/detail",
            params={"order_id": order_id},
            access_token=self.access_token,
        )
        order_info = result.get("order", {})
        return self._parse_order(order_info)
