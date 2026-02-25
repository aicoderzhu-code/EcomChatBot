"""
YunGouOS 聚合支付客户端

实现 PaymentGateway 接口，对接 YunGouOS 平台的微信/支付宝扫码支付。
"""
import hashlib
import logging
from typing import Optional

import httpx

from services.payment_gateway import PaymentGateway

logger = logging.getLogger(__name__)

WECHAT_NATIVE_URL = "https://api.pay.yungouos.com/api/pay/wxpay/nativePay"
WECHAT_QUERY_URL = "https://api.pay.yungouos.com/api/pay/wxpay/queryOrder"
ALIPAY_NATIVE_URL = "https://api.pay.yungouos.com/api/pay/alipay/nativePay"
ALIPAY_QUERY_URL = "https://api.pay.yungouos.com/api/pay/alipay/queryOrder"


def _md5_sign(params: dict, key: str) -> str:
    """
    YunGouOS MD5 签名

    规则：
    1. 收集所有非空参数（排除 sign 本身）
    2. 按 key 字母序升序排列
    3. 拼接为 key1=val1&key2=val2&...&key=商户密钥
    4. MD5 取 32 位大写
    """
    filtered = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
    sorted_items = sorted(filtered.items())
    query_str = "&".join(f"{k}={v}" for k, v in sorted_items)
    sign_str = f"{query_str}&key={key}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


class YunGouOSClient(PaymentGateway):
    """YunGouOS 聚合支付客户端"""

    def __init__(
        self,
        wechat_mch_id: str,
        wechat_key: str,
        alipay_mch_id: str,
        alipay_key: str,
        notify_url: str,
    ):
        self.wechat_mch_id = wechat_mch_id
        self.wechat_key = wechat_key
        self.alipay_mch_id = alipay_mch_id
        self.alipay_key = alipay_key
        self.notify_url = notify_url

    def _get_mch_id(self, channel: str) -> str:
        return self.wechat_mch_id if channel == "wechat" else self.alipay_mch_id

    def _get_key(self, channel: str) -> str:
        return self.wechat_key if channel == "wechat" else self.alipay_key

    async def create_native_pay(
        self,
        out_trade_no: str,
        total_fee: str,
        body: str,
        notify_url: str,
        channel: str,
        attach: str = "",
    ) -> dict:
        """创建扫码支付，返回 {"qr_url": str, "qr_base64": str | None}"""
        mch_id = self._get_mch_id(channel)
        key = self._get_key(channel)

        params: dict = {
            "out_trade_no": out_trade_no,
            "total_fee": total_fee,
            "mch_id": mch_id,
            "body": body,
            "notify_url": notify_url,
        }
        if attach:
            params["attach"] = attach

        params["sign"] = _md5_sign(params, key)

        url = WECHAT_NATIVE_URL if channel == "wechat" else ALIPAY_NATIVE_URL

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=params)
            resp.raise_for_status()
            result = resp.json()

        if result.get("code") != 0:
            raise RuntimeError(f"YunGouOS error: {result.get('msg', result)}")

        return {
            "qr_url": result.get("data", ""),
            "qr_base64": result.get("img"),
        }

    async def query_order(self, out_trade_no: str, channel: str) -> dict:
        """查询订单状态，返回 {"paid": bool, "trade_no": str, "amount": str}"""
        mch_id = self._get_mch_id(channel)
        key = self._get_key(channel)

        params = {
            "out_trade_no": out_trade_no,
            "mch_id": mch_id,
        }
        params["sign"] = _md5_sign(params, key)

        url = WECHAT_QUERY_URL if channel == "wechat" else ALIPAY_QUERY_URL

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            result = resp.json()

        if result.get("code") != 0:
            return {"paid": False, "trade_no": "", "amount": "0"}

        data = result.get("data") or {}
        # 微信返回 trade_state == "SUCCESS"，支付宝返回 trade_status == "TRADE_SUCCESS"
        paid = (
            data.get("trade_state") == "SUCCESS"
            or data.get("trade_status") == "TRADE_SUCCESS"
        )
        return {
            "paid": paid,
            "trade_no": data.get("transaction_id") or data.get("trade_no") or "",
            "amount": str(data.get("total_fee") or data.get("money") or "0"),
        }

    def verify_notify(self, params: dict) -> bool:
        """验证回调签名"""
        received_sign = params.get("sign", "")
        # 根据 out_trade_no 判断渠道（通过 attach 或其他字段）
        # YunGouOS 微信和支付宝回调格式相同，但 key 不同
        # 这里尝试两个 key，任一匹配即通过
        for key in [self.wechat_key, self.alipay_key]:
            if key and _md5_sign(params, key) == received_sign:
                return True
        return False

    async def refund(
        self,
        out_trade_no: str,
        refund_amount: str,
        refund_reason: str,
        channel: str,
    ) -> dict:
        """申请退款（YunGouOS 退款接口预留，实际接口以文档为准）"""
        logger.warning(
            f"YunGouOS refund called: out_trade_no={out_trade_no}, "
            f"amount={refund_amount}, channel={channel}"
        )
        # YunGouOS 退款接口需要根据实际文档实现
        return {"success": False, "refund_no": "", "message": "退款接口待接入"}


def get_yungouos_client() -> Optional[YunGouOSClient]:
    """获取 YunGouOS 客户端实例（从配置读取）"""
    from core.config import settings

    if not getattr(settings, "yungouos_wechat_mch_id", "") and not getattr(settings, "yungouos_alipay_mch_id", ""):
        logger.warning("YunGouOS 配置未设置")
        return None

    return YunGouOSClient(
        wechat_mch_id=getattr(settings, "yungouos_wechat_mch_id", ""),
        wechat_key=getattr(settings, "yungouos_wechat_key", ""),
        alipay_mch_id=getattr(settings, "yungouos_alipay_mch_id", ""),
        alipay_key=getattr(settings, "yungouos_alipay_key", ""),
        notify_url=getattr(settings, "yungouos_notify_url", ""),
    )
