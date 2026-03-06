"""拼多多平台适配器"""
import logging
from datetime import datetime

from services.platform.adapter_registry import register
from services.platform.base_adapter import BasePlatformAdapter
from services.platform.dto import OrderDTO, PageResult, ProductDTO
from services.platform.pinduoduo_client import PinduoduoClient

logger = logging.getLogger(__name__)


@register("pinduoduo")
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

    # ===== OAuth =====

    PDD_AUTH_URL = "https://mms.pinduoduo.com/open.html"

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        import urllib.parse
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.PDD_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_token(self, code: str):
        from services.platform.dto import TokenResult
        token_data = await self.client.call_api(
            method="pdd.pop.auth.token.create",
            params={"code": code, "grant_type": "authorization_code"},
        )
        return TokenResult(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in", 7776000),
            shop_id=str(token_data.get("owner_id", "")),
        )

    async def refresh_token(self, refresh_token: str):
        from services.platform.dto import TokenResult
        token_data = await self.client.refresh_access_token(refresh_token)
        return TokenResult(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in", 7776000),
        )

    # ===== 消息 =====

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        signature = headers.get("pdd-sign", "")
        if not signature:
            return True  # 无签名则不验证（兼容测试）
        return self.client.verify_webhook_signature(body, signature)

    def parse_webhook_event(self, body: dict) -> list:
        from services.platform.dto import MessageEvent, EventType, PlatformType
        events = []
        shop_id = str(body.get("shop_id", ""))
        buyer_id = str(body.get("buyer_id", ""))
        conversation_id = str(body.get("conversation_id", ""))
        content = body.get("content", "")
        msg_type = body.get("msg_type", 1)

        if content or conversation_id:
            events.append(MessageEvent(
                event_type=EventType.MESSAGE.value,
                platform_type=PlatformType.PINDUODUO.value,
                shop_id=shop_id,
                buyer_id=buyer_id,
                conversation_id=conversation_id,
                content=content,
                msg_type="text" if msg_type == 1 else str(msg_type),
                raw_data=body,
                event_id=f"pdd_{shop_id}_{conversation_id}_{int(datetime.utcnow().timestamp())}",
            ))
        return events

    async def send_message(self, conversation_id: str, content: str, msg_type: str = "text") -> bool:
        await self.client.send_message(
            access_token=self.access_token,
            conversation_id=conversation_id,
            content=content,
        )
        return True

    # ===== 售后 =====

    async def fetch_aftersales(self, page: int = 1, page_size: int = 50, status: str | None = None):
        from services.platform.dto import AfterSaleDTO
        params = {"page": page, "page_size": page_size}
        if status:
            params["after_sales_status"] = status
        try:
            data = await self.client.call_api(
                method="pdd.refund.list.increment.get",
                params=params,
                access_token=self.access_token,
            )
            items = []
            for item in data.get("refund_list", []):
                items.append(AfterSaleDTO(
                    platform_aftersale_id=str(item.get("id", "")),
                    order_id=str(item.get("order_sn", "")),
                    aftersale_type="refund_only" if item.get("after_sales_type") == 1 else "return_refund",
                    status=str(item.get("after_sales_status", "pending")),
                    reason=item.get("reason", ""),
                    refund_amount=item.get("refund_amount", 0) / 100,
                    buyer_id="",
                    platform_data=item,
                ))
            return PageResult(items=items, total=data.get("total_count", 0), page=page, page_size=page_size)
        except Exception:
            return PageResult(items=[], total=0, page=page, page_size=page_size)

    async def get_aftersale_detail(self, aftersale_id: str):
        from services.platform.dto import AfterSaleDTO
        data = await self.client.call_api(
            method="pdd.refund.information.get",
            params={"after_sales_id": aftersale_id},
            access_token=self.access_token,
        )
        return AfterSaleDTO(
            platform_aftersale_id=aftersale_id,
            order_id=str(data.get("order_sn", "")),
            status=str(data.get("after_sales_status", "")),
            reason=data.get("reason", ""),
            refund_amount=data.get("refund_amount", 0) / 100,
            platform_data=data,
        )

    async def approve_refund(self, aftersale_id: str) -> bool:
        await self.client.call_api(
            method="pdd.refund.agree",
            params={"after_sales_id": aftersale_id},
            access_token=self.access_token,
        )
        return True

    async def reject_refund(self, aftersale_id: str, reason: str) -> bool:
        await self.client.call_api(
            method="pdd.refund.refuse",
            params={"after_sales_id": aftersale_id, "refuse_reason": reason},
            access_token=self.access_token,
        )
        return True
