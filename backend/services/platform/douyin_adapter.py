"""抖音抖店平台适配器"""
import logging
from datetime import datetime
from typing import Any

from services.platform.adapter_registry import register
from services.platform.base_adapter import BasePlatformAdapter
from services.platform.dto import OrderDTO, PageResult, ProductDTO
from services.platform.douyin_client import DouyinClient

logger = logging.getLogger(__name__)


@register("douyin")
class DouyinAdapter(BasePlatformAdapter):
    """抖音抖店平台适配器"""

    def __init__(self, app_key: str, app_secret: str, access_token: str | None = None):
        super().__init__(app_key, app_secret, access_token)
        self.client = DouyinClient(app_key, app_secret)

    def _parse_product(self, raw: dict) -> ProductDTO:
        """将抖音商品原始数据转为 ProductDTO"""
        images = raw.get("pic") or raw.get("imgs") or raw.get("images") or []
        if isinstance(images, str):
            images = [images]
        videos = raw.get("video") or raw.get("videos") or []
        if isinstance(videos, str):
            videos = [videos]

        def _to_price(v: Any) -> float:
            if v is None:
                return 0.0
            # 抖店金额字段多数为分，兼容小数金额字段
            fv = float(v)
            return fv / 100 if fv >= 100 else fv

        return ProductDTO(
            platform_product_id=str(
                raw.get("product_id")
                or raw.get("id")
                or raw.get("out_product_id")
                or ""
            ),
            title=raw.get("name") or raw.get("title") or "",
            price=_to_price(raw.get("price")),
            original_price=_to_price(raw.get("market_price")) if raw.get("market_price") else None,
            description=raw.get("description", ""),
            category=raw.get("category_name", ""),
            images=images,
            videos=videos,
            attributes=raw.get("spec_list") or raw.get("specs"),
            sales_count=int(raw.get("sales") or raw.get("sale_num") or 0),
            stock=int(raw.get("stock_num") or raw.get("stock") or 0),
            status="active" if int(raw.get("status", 1) or 1) in (1, 105) else "inactive",
            platform_data=raw,
        )

    async def fetch_products(self, page: int = 1, page_size: int = 50) -> PageResult:
        """拉取抖音商品列表"""
        result = await self.client.call_api(
            endpoint="/product/listV2",
            api_method="product.listV2",
            params={
                "page": page,
                "size": page_size,
            },
            access_token=self.access_token,
        )

        product_list = (
            result.get("list")
            or result.get("product_list")
            or result.get("products")
            or []
        )
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
            api_method="product.detail",
            params={"product_id": product_id},
            access_token=self.access_token,
        )
        product_info = result.get("product") or result
        return self._parse_product(product_info)

    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        """拉取指定时间后变更的商品"""
        timestamp = int(since.timestamp())
        result = await self.client.call_api(
            endpoint="/product/listV2",
            api_method="product.listV2",
            params={
                "page": 1,
                "size": 100,
                "update_time_start": timestamp,
            },
            access_token=self.access_token,
        )
        product_list = result.get("list") or result.get("product_list") or []
        return [self._parse_product(p) for p in product_list]

    async def upload_image(self, product_id: str, image_url: str) -> str:
        """上传图片到抖音"""
        result = await self.client.call_api(
            endpoint="/material/upload_image_by_url",
            api_method="material.upload_image_by_url",
            params={"url": image_url},
            access_token=self.access_token,
        )
        return result.get("url", "")

    async def upload_video(self, product_id: str, video_url: str) -> str:
        """上传视频到抖音"""
        result = await self.client.call_api(
            endpoint="/material/upload_video_by_url",
            api_method="material.upload_video_by_url",
            params={"url": video_url},
            access_token=self.access_token,
        )
        return result.get("video_id", "")

    async def update_product(self, product_id: str, data: dict) -> bool:
        """更新抖音商品信息"""
        params = {"product_id": product_id, **data}
        try:
            await self.client.call_api(
                endpoint="/product/editV2",
                api_method="product.editV2",
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
            params["create_time_start"] = int(start_time.timestamp())
        if end_time:
            params["create_time_end"] = int(end_time.timestamp())
        if status:
            # 抖店主状态过滤
            status_map = {
                "pending": 1,
                "paid": 2,
                "shipped": 3,
                "completed": 5,
                "cancelled": 4,
            }
            if status in status_map:
                params["main_status"] = status_map[status]

        result = await self.client.call_api(
            endpoint="/order/searchList",
            api_method="order.searchList",
            params=params,
            access_token=self.access_token,
        )

        order_list = result.get("shop_order_list", [])
        total = result.get("total", 0)

        orders = [self._parse_order(o) for o in order_list]

        return PageResult(items=orders, total=total, page=page, page_size=page_size)

    @staticmethod
    def _parse_ts(ts: Any) -> datetime | None:
        if not ts:
            return None
        try:
            return datetime.fromtimestamp(int(ts))
        except Exception:
            return None

    def _parse_order(self, raw: dict) -> OrderDTO:
        """将抖音订单原始数据转为 OrderDTO"""
        return OrderDTO(
            platform_order_id=str(raw.get("order_id") or ""),
            product_id=str(raw.get("product_id", "")),
            product_title=raw.get("product_name", ""),
            buyer_id=str(raw.get("doudian_open_id") or raw.get("open_id") or raw.get("buyer_id") or ""),
            quantity=raw.get("item_num", 1),
            unit_price=float(raw.get("order_amount", 0)) / 100 if raw.get("order_amount") else 0.0,
            total_amount=float(raw.get("pay_amount", 0)) / 100 if raw.get("pay_amount") else 0.0,
            status=self._map_order_status(raw.get("order_status") or raw.get("main_status") or 0),
            paid_at=self._parse_ts(raw.get("pay_time")),
            shipped_at=self._parse_ts(raw.get("exp_ship_time")),
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
            endpoint="/order/orderDetail",
            api_method="order.orderDetail",
            params={"shop_order_id": order_id},
            access_token=self.access_token,
        )
        order_info = result.get("shop_order_detail", {})
        return self._parse_order(order_info)

    # ===== OAuth =====

    DOUYIN_AUTH_URL = "https://open.douyin.com/platform/oauth/connect"

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        import urllib.parse
        params = {
            "response_type": "code",
            "app_id": self.app_key,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.DOUYIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_token(self, code: str):
        from services.platform.dto import TokenResult
        data = await self.client.create_access_token(code=code)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 86400),
            shop_id=str(data.get("shop_id", "")),
            shop_name=data.get("shop_name"),
        )

    async def refresh_token(self, refresh_token: str):
        from services.platform.dto import TokenResult
        data = await self.client.refresh_access_token(refresh_token)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 86400),
        )

    # ===== 消息 =====

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        signature = headers.get("event-sign", "")
        if not signature:
            return True  # 无签名则不验证（兼容测试）
        app_id = headers.get("app-id", self.app_key)
        sign_method = headers.get("sign-method")
        return self.client.verify_webhook_signature(body, signature, app_id, sign_method)

    def parse_webhook_event(self, body: dict) -> list:
        import json as _json
        from services.platform.dto import MessageEvent, EventType, PlatformType

        events = []

        # 兼容两种格式
        messages = body.get("messages") or body.get("data") or []
        if not messages and body.get("content"):
            # 旧格式：直接字段
            messages = [body]

        for msg in messages:
            shop_id = str(msg.get("shop_id") or msg.get("ShopId") or "")
            buyer_id = str(msg.get("buyer_id") or msg.get("doudian_open_id") or msg.get("open_id") or "")
            conversation_id = str(msg.get("conversation_id") or msg.get("conv_id") or "")

            # 提取消息内容
            content = msg.get("content", "")
            if isinstance(content, str):
                try:
                    content_data = _json.loads(content)
                    content = content_data.get("text", content)
                except Exception:
                    pass

            if content or conversation_id:
                events.append(MessageEvent(
                    event_type=EventType.MESSAGE.value,
                    platform_type=PlatformType.DOUYIN.value,
                    shop_id=shop_id,
                    buyer_id=buyer_id,
                    conversation_id=conversation_id,
                    content=content,
                    msg_type="text",
                    raw_data=msg,
                    event_id=str(msg.get("msg_id") or msg.get("event_id") or f"dy_{shop_id}_{int(datetime.utcnow().timestamp())}"),
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
        params: dict = {"page": page, "size": page_size}
        if status:
            params["aftersale_status"] = status
        try:
            data = await self.client.call_api(
                endpoint="/afterSale/List",
                api_method="afterSale.List",
                params=params,
                access_token=self.access_token,
            )
            items = []
            for item in data.get("aftersale_list", []):
                items.append(AfterSaleDTO(
                    platform_aftersale_id=str(item.get("aftersale_id", "")),
                    order_id=str(item.get("order_id", "")),
                    aftersale_type="refund_only" if item.get("aftersale_type") == 0 else "return_refund",
                    status=str(item.get("aftersale_status", "pending")),
                    reason=item.get("reason", ""),
                    refund_amount=float(item.get("refund_amount", 0)) / 100,
                    buyer_id=str(item.get("open_id", "")),
                    platform_data=item,
                ))
            return PageResult(items=items, total=data.get("total", 0), page=page, page_size=page_size)
        except Exception:
            return PageResult(items=[], total=0, page=page, page_size=page_size)

    async def get_aftersale_detail(self, aftersale_id: str):
        from services.platform.dto import AfterSaleDTO
        data = await self.client.call_api(
            endpoint="/afterSale/Detail",
            api_method="afterSale.Detail",
            params={"aftersale_id": aftersale_id},
            access_token=self.access_token,
        )
        return AfterSaleDTO(
            platform_aftersale_id=aftersale_id,
            order_id=str(data.get("order_id", "")),
            status=str(data.get("aftersale_status", "")),
            reason=data.get("reason", ""),
            refund_amount=float(data.get("refund_amount", 0)) / 100,
            platform_data=data,
        )

    async def approve_refund(self, aftersale_id: str) -> bool:
        await self.client.call_api(
            endpoint="/afterSale/Agree",
            api_method="afterSale.Agree",
            params={"aftersale_id": aftersale_id},
            access_token=self.access_token,
        )
        return True

    async def reject_refund(self, aftersale_id: str, reason: str) -> bool:
        await self.client.call_api(
            endpoint="/afterSale/Reject",
            api_method="afterSale.Reject",
            params={"aftersale_id": aftersale_id, "reason": reason},
            access_token=self.access_token,
        )
        return True
