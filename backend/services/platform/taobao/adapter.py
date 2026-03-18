"""淘宝/天猫平台适配器

⚠️ 重要限制说明 — 旺旺 IM 聊天客服对第三方封闭
=================================================
淘宝开放平台自 2016 年起对客服类 ISV 强管控：
- 旺旺 IM 聊天消息 API（含聊天记录增值包）仅对"绩效考核类功能应用"开放
- AI 智能客服 SaaS 属于客服类应用，**无法通过标准申请获批**
- 阿里巴巴有自己的 AI 客服生态（千牛智能客服），不开放第三方竞争

本适配器的 IM 实现（parse_webhook_event / send_message）使用的是：
  taobao.miniapp.message.send — 小程序客服消息接口（非旺旺 IM）

该绕路方案的覆盖范围极其有限：
  ✅ 仅适用于商家已开通淘宝/天猫小程序的场景
  ❌ 不适用于常规旺旺 IM 聊天场景（覆盖绝大多数商家）

建议：
  - 淘宝/天猫接入定位应调整为"商品/订单/售后数据同步"，不承诺 IM 聊天客服
  - 若要做旺旺 IM 客服，需走千牛 ISV 合作路线（需单独商务谈判，非技术问题）
  - 向商家明确说明本产品在淘宝侧的功能边界
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
from services.platform.taobao.client import TaobaoClient

logger = logging.getLogger(__name__)

TAOBAO_AUTH_URL = "https://oauth.taobao.com/authorize"


@register("taobao")
class TaobaoAdapter(BasePlatformAdapter):
    """淘宝/天猫平台适配器"""

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        import urllib.parse
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "redirect_uri": redirect_uri,
            "state": state,
            "view": "web",
        }
        return f"{TAOBAO_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_token(self, code: str) -> TokenResult:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.get_access_token(code)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 86400)),
            shop_id=str(data.get("taobao_user_id", "")),
            shop_name=data.get("taobao_user_nick"),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResult:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.refresh_access_token(refresh_token)
        return TokenResult(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 86400)),
        )

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        signature = headers.get("sign", "") or headers.get("x-sign", "")
        if not signature:
            return True
        client = TaobaoClient(self.app_key, self.app_secret)
        return client.verify_webhook_signature(body, signature)

    def parse_webhook_event(self, body: dict) -> list[PlatformEvent]:
        # ⚠️ 注意：此处解析的是淘宝小程序客服消息（TMC 通道），非旺旺 IM 消息。
        # 仅在商家开通小程序后才有消息推送，覆盖范围极为有限。
        events = []
        # 淘宝消息通道 (TMC) 格式
        messages = body.get("messages", [body]) if isinstance(body, dict) else [body]
        for msg in messages:
            topic = msg.get("topic", "")
            if "trade" in topic or "refund" in topic:
                pass
            else:
                content_data = msg.get("content", {})
                if isinstance(content_data, str):
                    try:
                        content_data = json.loads(content_data)
                    except Exception:
                        content_data = {"text": content_data}

                events.append(MessageEvent(
                    event_type=EventType.MESSAGE.value,
                    platform_type=PlatformType.TAOBAO.value,
                    shop_id=str(msg.get("user_id", "")),
                    buyer_id=str(content_data.get("buyer_nick", "")),
                    conversation_id=str(content_data.get("session_id", "")),
                    content=content_data.get("text", ""),
                    msg_type="text",
                    raw_data=msg,
                    event_id=str(msg.get("id", "")),
                ))
        return events

    async def send_message(self, conversation_id: str, content: str, msg_type: str = "text") -> bool:
        # ⚠️ 注意：此处调用的是淘宝小程序客服消息接口（taobao.miniapp.message.send），
        # 非旺旺 IM 接口。仅在商家开通小程序时可用，无法覆盖常规淘宝/天猫旺旺 IM 场景。
        client = TaobaoClient(self.app_key, self.app_secret)
        await client.send_message(
            session_key=self.access_token,
            buyer_nick=conversation_id,
            content=content,
        )
        return True

    # ===== 商品 =====
    async def fetch_products(self, page=1, page_size=50) -> PageResult:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="taobao.items.onsale.get",
            params={"page_no": page, "page_size": page_size, "fields": "num_iid,title,price,pic_url,num,list_time"},
            session_key=self.access_token,
        )
        items = []
        for item in data.get("items", {}).get("item", []):
            items.append(ProductDTO(
                platform_product_id=str(item.get("num_iid", "")),
                title=item.get("title", ""),
                price=float(item.get("price", 0)),
                images=[item.get("pic_url", "")] if item.get("pic_url") else [],
                stock=item.get("num", 0),
                platform_data=item,
            ))
        return PageResult(items=items, total=data.get("total_results", 0), page=page, page_size=page_size)

    async def fetch_product_detail(self, product_id: str) -> ProductDTO:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="taobao.item.seller.get",
            params={"num_iid": product_id, "fields": "num_iid,title,price,desc,pic_url,item_imgs,num"},
            session_key=self.access_token,
        )
        item = data.get("item", {})
        images = [img.get("url", "") for img in item.get("item_imgs", {}).get("item_img", [])]
        return ProductDTO(
            platform_product_id=str(item.get("num_iid", "")),
            title=item.get("title", ""),
            price=float(item.get("price", 0)),
            description=item.get("desc", ""),
            images=images,
            stock=item.get("num", 0),
            platform_data=item,
        )

    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="taobao.items.onsale.get",
            params={
                "start_modified": since.strftime("%Y-%m-%d %H:%M:%S"),
                "fields": "num_iid,title,price,pic_url,num",
                "page_size": 200,
            },
            session_key=self.access_token,
        )
        items = []
        for item in data.get("items", {}).get("item", []):
            items.append(ProductDTO(
                platform_product_id=str(item.get("num_iid", "")),
                title=item.get("title", ""),
                price=float(item.get("price", 0)),
                images=[item.get("pic_url", "")] if item.get("pic_url") else [],
                stock=item.get("num", 0),
                platform_data=item,
            ))
        return items

    async def upload_image(self, product_id: str, image_url: str) -> str:
        raise NotImplementedError("淘宝图片上传需要特殊授权")

    async def upload_video(self, product_id: str, video_url: str) -> str:
        raise NotImplementedError("淘宝视频上传需要特殊授权")

    async def update_product(self, product_id: str, data: dict) -> bool:
        client = TaobaoClient(self.app_key, self.app_secret)
        params = {"num_iid": product_id}
        params.update(data)
        await client.call_api(method="taobao.item.update", params=params, session_key=self.access_token)
        return True

    # ===== 订单 =====
    async def fetch_orders(self, page=1, page_size=50, start_time=None, end_time=None, status=None) -> PageResult:
        client = TaobaoClient(self.app_key, self.app_secret)
        params = {
            "page_no": page,
            "page_size": page_size,
            "fields": "tid,payment,status,created,pay_time,consign_time,end_time,buyer_nick,num,title,price,total_fee",
        }
        if start_time:
            params["start_created"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        if end_time:
            params["end_created"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        if status:
            params["status"] = status

        data = await client.call_api(method="taobao.trades.sold.get", params=params, session_key=self.access_token)
        items = []
        for trade in data.get("trades", {}).get("trade", []):
            items.append(OrderDTO(
                platform_order_id=str(trade.get("tid", "")),
                product_title=trade.get("title", ""),
                buyer_id=trade.get("buyer_nick", ""),
                quantity=trade.get("num", 1),
                total_amount=float(trade.get("total_fee", 0)),
                status=trade.get("status", ""),
                platform_data=trade,
            ))
        return PageResult(items=items, total=data.get("total_results", 0), page=page, page_size=page_size)

    async def fetch_order_detail(self, order_id: str) -> OrderDTO:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="taobao.trade.fullinfo.get",
            params={"tid": order_id, "fields": "tid,payment,status,created,pay_time,consign_time,end_time,buyer_nick,num,title,price,total_fee,refund_fee"},
            session_key=self.access_token,
        )
        trade = data.get("trade", {})
        return OrderDTO(
            platform_order_id=str(trade.get("tid", "")),
            product_title=trade.get("title", ""),
            buyer_id=trade.get("buyer_nick", ""),
            quantity=trade.get("num", 1),
            total_amount=float(trade.get("total_fee", 0)),
            status=trade.get("status", ""),
            refund_amount=float(trade.get("refund_fee", 0)) if trade.get("refund_fee") else None,
            platform_data=trade,
        )

    # ===== 售后 =====
    async def fetch_aftersales(self, page=1, page_size=50, status=None) -> PageResult:
        client = TaobaoClient(self.app_key, self.app_secret)
        params = {"page_no": page, "page_size": page_size, "fields": "refund_id,tid,status,reason,refund_fee,created"}
        if status:
            params["status"] = status
        data = await client.call_api(method="taobao.refunds.receive.get", params=params, session_key=self.access_token)
        items = []
        for refund in data.get("refunds", {}).get("refund", []):
            items.append(AfterSaleDTO(
                platform_aftersale_id=str(refund.get("refund_id", "")),
                order_id=str(refund.get("tid", "")),
                status=refund.get("status", ""),
                reason=refund.get("reason", ""),
                refund_amount=float(refund.get("refund_fee", 0)),
                platform_data=refund,
            ))
        return PageResult(items=items, total=data.get("total_results", 0), page=page, page_size=page_size)

    async def get_aftersale_detail(self, aftersale_id: str) -> AfterSaleDTO:
        client = TaobaoClient(self.app_key, self.app_secret)
        data = await client.call_api(
            method="taobao.refund.get",
            params={"refund_id": aftersale_id, "fields": "refund_id,tid,status,reason,refund_fee"},
            session_key=self.access_token,
        )
        refund = data.get("refund", {})
        return AfterSaleDTO(
            platform_aftersale_id=str(refund.get("refund_id", "")),
            order_id=str(refund.get("tid", "")),
            status=refund.get("status", ""),
            reason=refund.get("reason", ""),
            refund_amount=float(refund.get("refund_fee", 0)),
            platform_data=refund,
        )

    async def approve_refund(self, aftersale_id: str) -> bool:
        client = TaobaoClient(self.app_key, self.app_secret)
        await client.call_api(
            method="taobao.refund.agree",
            params={"refund_id": aftersale_id},
            session_key=self.access_token,
        )
        return True

    async def reject_refund(self, aftersale_id: str, reason: str) -> bool:
        client = TaobaoClient(self.app_key, self.app_secret)
        await client.call_api(
            method="taobao.refund.refuse",
            params={"refund_id": aftersale_id, "refuse_message": reason},
            session_key=self.access_token,
        )
        return True
