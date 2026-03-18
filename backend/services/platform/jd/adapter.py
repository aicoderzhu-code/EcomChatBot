"""京东平台适配器

⚠️ 重要说明 — 京东咚咚 IM 第三方接入状态待验证
================================================
京东宙斯开放平台（JOS）对商品/订单/售后 API 完全开放，但 IM 客服消息接口状态不明确：
- 京东有"咚咚"即时通讯系统，但第三方 ISV 能否接入尚无公开文档
- 当前 parse_webhook_event / send_message 方法属于**推测性实现**，参考了可能的字段格式
- 在实际注册 JD ISV 账号并测试前，IM 功能不可依赖

建议：
  - 正式开发 JD IM 功能前，先注册京东开放平台 ISV 账号，验证以下两点：
    1. 是否有专门的客服消息推送接口（Webhook 订阅）
    2. 是否有回复消息的 API
  - 若 JD IM API 也封闭（与淘宝类似），将接入定位改为"商品/订单/售后数据同步"
"""
import json
import logging
from datetime import datetime

from services.platform.adapter_registry import register
from services.platform.base_adapter import BasePlatformAdapter
from services.platform.dto import (
    ProductDTO, OrderDTO, AfterSaleDTO, PageResult, TokenResult,
    PlatformEvent, MessageEvent, EventType, PlatformType,
)
from services.platform.jd.client import JdClient

logger = logging.getLogger(__name__)

JD_AUTH_URL = "https://oauth.jd.com/oauth/authorize"


@register("jd")
class JdAdapter(BasePlatformAdapter):
    """京东平台适配器"""

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        import urllib.parse
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{JD_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_token(self, code: str) -> TokenResult:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.get_access_token(code)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 86400)),
            shop_id=str(data.get("uid", "")),
            shop_name=data.get("user_nick"),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResult:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.refresh_access_token(refresh_token)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 86400)),
        )

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        signature = headers.get("jd-sign", "") or headers.get("x-jd-sign", "")
        if not signature:
            return True
        client = JdClient(self.app_key, self.app_secret)
        return client.verify_webhook_signature(body, signature)

    def parse_webhook_event(self, body: dict) -> list[PlatformEvent]:
        # ⚠️ 推测性实现：JD 咚咚 IM Webhook 格式未经实测验证，字段名称可能不正确。
        # 需注册京东 ISV 账号并实测后再确认。
        events = []
        messages = body.get("messages", [body]) if isinstance(body, dict) else [body]
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                try:
                    content_data = json.loads(content)
                    content = content_data.get("text", content)
                except Exception:
                    pass

            shop_id = str(msg.get("shop_id") or msg.get("vender_id") or "")
            buyer_id = str(msg.get("buyer_id") or msg.get("customer_id") or "")
            conversation_id = str(msg.get("conversation_id") or msg.get("session_id") or "")

            if content or conversation_id:
                events.append(MessageEvent(
                    event_type=EventType.MESSAGE.value,
                    platform_type=PlatformType.JD.value,
                    shop_id=shop_id,
                    buyer_id=buyer_id,
                    conversation_id=conversation_id,
                    content=content,
                    msg_type="text",
                    raw_data=msg,
                    event_id=str(msg.get("msg_id") or f"jd_{shop_id}_{int(datetime.utcnow().timestamp())}"),
                ))
        return events

    async def send_message(self, conversation_id: str, content: str, msg_type: str = "text") -> bool:
        # ⚠️ 推测性实现：JD 咚咚消息回复 API 未经实测验证，方法名和参数格式可能不正确。
        # 需注册京东 ISV 账号并确认 IM API 可用性后再启用。
        client = JdClient(self.app_key, self.app_secret)
        await client.send_message(
            access_token=self.access_token,
            customer_id=conversation_id,
            content=content,
        )
        return True

    # ===== 商品 =====
    async def fetch_products(self, page=1, page_size=50) -> PageResult:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="jd.ware.listing.get",
            params={"page": page, "page_size": page_size},
            access_token=self.access_token,
        )
        items = []
        for item in data.get("ware_infos", []):
            items.append(ProductDTO(
                platform_product_id=str(item.get("ware_id", "")),
                title=item.get("title", ""),
                price=float(item.get("jd_price", 0)),
                original_price=float(item.get("market_price", 0)) if item.get("market_price") else None,
                images=[item.get("logo", "")] if item.get("logo") else [],
                stock=item.get("stock_num", 0),
                status="active" if item.get("ware_status") == 1 else "inactive",
                platform_data=item,
            ))
        return PageResult(items=items, total=data.get("total", 0), page=page, page_size=page_size)

    async def fetch_product_detail(self, product_id: str) -> ProductDTO:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="jd.ware.get",
            params={"ware_id": product_id},
            access_token=self.access_token,
        )
        item = data.get("ware_info", data)
        images = item.get("images", [])
        if isinstance(images, str):
            images = [images]
        return ProductDTO(
            platform_product_id=str(item.get("ware_id", "")),
            title=item.get("title", ""),
            price=float(item.get("jd_price", 0)),
            original_price=float(item.get("market_price", 0)) if item.get("market_price") else None,
            description=item.get("introduction", ""),
            images=images,
            stock=item.get("stock_num", 0),
            platform_data=item,
        )

    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="jd.ware.listing.get",
            params={
                "page": 1,
                "page_size": 100,
                "start_modified": since.strftime("%Y-%m-%d %H:%M:%S"),
            },
            access_token=self.access_token,
        )
        items = []
        for item in data.get("ware_infos", []):
            items.append(ProductDTO(
                platform_product_id=str(item.get("ware_id", "")),
                title=item.get("title", ""),
                price=float(item.get("jd_price", 0)),
                images=[item.get("logo", "")] if item.get("logo") else [],
                stock=item.get("stock_num", 0),
                platform_data=item,
            ))
        return items

    async def upload_image(self, product_id: str, image_url: str) -> str:
        raise NotImplementedError("京东图片上传需要特殊授权")

    async def upload_video(self, product_id: str, video_url: str) -> str:
        raise NotImplementedError("京东视频上传需要特殊授权")

    async def update_product(self, product_id: str, data: dict) -> bool:
        client = JdClient(self.app_key, self.app_secret)
        params = {"ware_id": product_id}
        params.update(data)
        await client.call_api(method="jd.ware.update", params=params, access_token=self.access_token)
        return True

    # ===== 订单 =====
    async def fetch_orders(self, page=1, page_size=50, start_time=None, end_time=None, status=None) -> PageResult:
        client = JdClient(self.app_key, self.app_secret)
        params: dict = {"page": page, "page_size": page_size}
        if start_time:
            params["start_date"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        if end_time:
            params["end_date"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        if status:
            params["order_state"] = status

        data = await client.call_api(method="jd.pop.order.search", params=params, access_token=self.access_token)
        items = []
        for order in data.get("order_search", []):
            items.append(OrderDTO(
                platform_order_id=str(order.get("order_id", "")),
                product_title=order.get("item_name", ""),
                buyer_id=str(order.get("buyer_id", "")),
                quantity=order.get("item_total", 1),
                total_amount=float(order.get("order_total_price", 0)),
                status=order.get("order_state", ""),
                platform_data=order,
            ))
        return PageResult(items=items, total=data.get("order_total", 0), page=page, page_size=page_size)

    async def fetch_order_detail(self, order_id: str) -> OrderDTO:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="jd.pop.order.get",
            params={"order_id": order_id},
            access_token=self.access_token,
        )
        order = data.get("order_info", data)
        return OrderDTO(
            platform_order_id=str(order.get("order_id", "")),
            product_title=order.get("item_name", ""),
            buyer_id=str(order.get("buyer_id", "")),
            quantity=order.get("item_total", 1),
            total_amount=float(order.get("order_total_price", 0)),
            status=order.get("order_state", ""),
            refund_amount=float(order.get("refund_price", 0)) if order.get("refund_price") else None,
            platform_data=order,
        )

    # ===== 售后 =====
    async def fetch_aftersales(self, page=1, page_size=50, status=None) -> PageResult:
        client = JdClient(self.app_key, self.app_secret)
        params: dict = {"page_index": page, "page_size": page_size}
        if status:
            params["status"] = status
        try:
            data = await client.call_api(
                method="jd.pop.afs.soa.refund.applyList",
                params=params,
                access_token=self.access_token,
            )
            items = []
            for item in data.get("result", []):
                items.append(AfterSaleDTO(
                    platform_aftersale_id=str(item.get("afs_service_id", "")),
                    order_id=str(item.get("order_id", "")),
                    aftersale_type="refund_only" if item.get("customer_expect_comp") == 1 else "return_refund",
                    status=str(item.get("afs_service_step", "")),
                    reason=item.get("question_desc", ""),
                    refund_amount=float(item.get("apply_refund_sum", 0)),
                    buyer_id=str(item.get("customer_id", "")),
                    platform_data=item,
                ))
            return PageResult(items=items, total=data.get("total_count", 0), page=page, page_size=page_size)
        except Exception:
            return PageResult(items=[], total=0, page=page, page_size=page_size)

    async def get_aftersale_detail(self, aftersale_id: str) -> AfterSaleDTO:
        client = JdClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="jd.pop.afs.soa.refund.info",
            params={"afs_service_id": aftersale_id},
            access_token=self.access_token,
        )
        item = data.get("result", data)
        return AfterSaleDTO(
            platform_aftersale_id=aftersale_id,
            order_id=str(item.get("order_id", "")),
            status=str(item.get("afs_service_step", "")),
            reason=item.get("question_desc", ""),
            refund_amount=float(item.get("apply_refund_sum", 0)),
            platform_data=item,
        )

    async def approve_refund(self, aftersale_id: str) -> bool:
        client = JdClient(self.app_key, self.app_secret)
        await client.call_api(
            method="jd.pop.afs.soa.refund.approve",
            params={"afs_service_id": aftersale_id},
            access_token=self.access_token,
        )
        return True

    async def reject_refund(self, aftersale_id: str, reason: str) -> bool:
        client = JdClient(self.app_key, self.app_secret)
        await client.call_api(
            method="jd.pop.afs.soa.refund.refuse",
            params={"afs_service_id": aftersale_id, "refuse_reason": reason},
            access_token=self.access_token,
        )
        return True
