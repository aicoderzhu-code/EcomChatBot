"""拼多多平台适配器"""
import logging
from datetime import datetime

from services.platform.base_adapter import (
    BasePlatformAdapter, OrderDTO, PageResult, ProductDTO,
)
from services.platform.pinduoduo_client import PinduoduoClient

logger = logging.getLogger(__name__)


class PddAdapter(BasePlatformAdapter):
    """拼多多平台适配器"""

    def __init__(self, app_key: str, app_secret: str, access_token: str | None = None):
        super().__init__(app_key, app_secret, access_token)
        self.client = PinduoduoClient(app_key, app_secret)

    def _parse_product(self, raw: dict) -> ProductDTO:
        """将拼多多商品原始数据转为 ProductDTO"""
        images = []
        if raw.get("image_url"):
            images.append(raw["image_url"])
        if raw.get("thumb_url"):
            images.extend(raw.get("carousel_gallery_list", []))

        return ProductDTO(
            platform_product_id=str(raw.get("goods_id", "")),
            title=raw.get("goods_name", ""),
            price=float(raw.get("min_group_price", 0)) / 100,  # 拼多多价格单位为分
            original_price=float(raw.get("min_normal_price", 0)) / 100 if raw.get("min_normal_price") else None,
            description=raw.get("goods_desc", ""),
            category=raw.get("category_name", ""),
            images=images,
            videos=[],
            attributes=raw.get("sku_list"),
            sales_count=raw.get("sold_quantity", 0),
            stock=raw.get("goods_quantity", 0),
            status="active" if raw.get("is_onsale") else "inactive",
            platform_data=raw,
        )

    async def fetch_products(self, page: int = 1, page_size: int = 50) -> PageResult:
        """拉取拼多多商品列表"""
        result = await self.client.call_api(
            method="pdd.goods.list.get",
            params={
                "page": str(page),
                "page_size": str(page_size),
                "outer_goods_id": "",
            },
            access_token=self.access_token,
        )

        response = result.get("goods_list_get_response", {})
        goods_list = response.get("goods_list", [])
        total = response.get("total_count", 0)

        products = [self._parse_product(g) for g in goods_list]

        return PageResult(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def fetch_product_detail(self, product_id: str) -> ProductDTO:
        """获取拼多多商品详情"""
        result = await self.client.call_api(
            method="pdd.goods.information.get",
            params={"goods_id": product_id},
            access_token=self.access_token,
        )
        goods_info = result.get("goods_information_get_response", {}).get("goods_info", {})
        return self._parse_product(goods_info)

    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        """拉取指定时间后变更的商品"""
        timestamp = int(since.timestamp())
        result = await self.client.call_api(
            method="pdd.goods.list.get",
            params={
                "page": "1",
                "page_size": "100",
                "update_start_time": str(timestamp),
            },
            access_token=self.access_token,
        )
        response = result.get("goods_list_get_response", {})
        goods_list = response.get("goods_list", [])
        return [self._parse_product(g) for g in goods_list]

    async def upload_image(self, product_id: str, image_url: str) -> str:
        """上传图片到拼多多"""
        result = await self.client.call_api(
            method="pdd.goods.image.upload",
            params={"image_url": image_url},
            access_token=self.access_token,
        )
        return result.get("goods_image_upload_response", {}).get("image_url", "")

    async def upload_video(self, product_id: str, video_url: str) -> str:
        """上传视频到拼多多"""
        result = await self.client.call_api(
            method="pdd.goods.video.upload",
            params={"video_url": video_url},
            access_token=self.access_token,
        )
        return result.get("goods_video_upload_response", {}).get("video_id", "")

    async def update_product(self, product_id: str, data: dict) -> bool:
        """更新拼多多商品信息"""
        params = {"goods_id": product_id, **data}
        result = await self.client.call_api(
            method="pdd.goods.information.update",
            params=params,
            access_token=self.access_token,
        )
        return "error_response" not in result

    async def fetch_orders(
        self,
        page: int = 1,
        page_size: int = 50,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
    ) -> PageResult:
        """拉取拼多多订单列表"""
        params: dict = {
            "page": str(page),
            "page_size": str(page_size),
        }
        if start_time:
            params["start_confirm_at"] = str(int(start_time.timestamp()))
        if end_time:
            params["end_confirm_at"] = str(int(end_time.timestamp()))
        if status:
            # 拼多多订单状态映射
            status_map = {
                "pending": "1",
                "paid": "2",
                "shipped": "3",
                "completed": "5",
            }
            if status in status_map:
                params["order_status"] = status_map[status]

        result = await self.client.call_api(
            method="pdd.order.list.get",
            params=params,
            access_token=self.access_token,
        )

        response = result.get("order_list_get_response", {})
        order_list = response.get("order_list", [])
        total = response.get("total_count", 0)

        orders = [self._parse_order(o) for o in order_list]

        return PageResult(items=orders, total=total, page=page, page_size=page_size)

    def _parse_order(self, raw: dict) -> OrderDTO:
        """将拼多多订单原始数据转为 OrderDTO"""
        return OrderDTO(
            platform_order_id=str(raw.get("order_sn", "")),
            product_id=str(raw.get("goods_id", "")),
            product_title=raw.get("goods_name", ""),
            buyer_id=str(raw.get("buyer_id", "")),
            quantity=raw.get("goods_count", 1),
            unit_price=float(raw.get("goods_price", 0)) / 100,
            total_amount=float(raw.get("pay_amount", 0)) / 100,
            status=self._map_order_status(raw.get("order_status", 0)),
            paid_at=datetime.fromtimestamp(raw["confirm_time"]) if raw.get("confirm_time") else None,
            shipped_at=datetime.fromtimestamp(raw["shipping_time"]) if raw.get("shipping_time") else None,
            platform_data=raw,
        )

    @staticmethod
    def _map_order_status(pdd_status: int) -> str:
        """拼多多订单状态映射"""
        status_map = {
            1: "pending",
            2: "paid",
            3: "shipped",
            5: "completed",
            6: "refunded",
            7: "cancelled",
        }
        return status_map.get(pdd_status, "pending")

    async def fetch_order_detail(self, order_id: str) -> OrderDTO:
        """获取拼多多订单详情"""
        result = await self.client.call_api(
            method="pdd.order.information.get",
            params={"order_sn": order_id},
            access_token=self.access_token,
        )
        order_info = result.get("order_information_get_response", {}).get("order_info", {})
        return self._parse_order(order_info)
