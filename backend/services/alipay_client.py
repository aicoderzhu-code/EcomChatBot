"""
支付宝官方 API 客户端

使用 RSA2 签名直接对接支付宝开放平台，支持：
- 当面付（扫码支付）：alipay.trade.precreate
- 订单查询：alipay.trade.query
- 退款：alipay.trade.refund
- 回调验签
"""
import base64
import json
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, utils

from services.payment_gateway import PaymentGateway

logger = logging.getLogger(__name__)


def _load_private_key(key_str: str):
    """加载 PEM 格式私钥"""
    key_data = key_str.strip()
    if not key_data.startswith("-----BEGIN"):
        # 纯 base64 内容，补全 PEM 头尾
        key_data = f"-----BEGIN RSA PRIVATE KEY-----\n{key_data}\n-----END RSA PRIVATE KEY-----"
    return serialization.load_pem_private_key(key_data.encode(), password=None)


def _load_public_key(key_str: str):
    """加载 PEM 格式公钥"""
    key_data = key_str.strip()
    if not key_data.startswith("-----BEGIN"):
        key_data = f"-----BEGIN PUBLIC KEY-----\n{key_data}\n-----END PUBLIC KEY-----"
    return serialization.load_pem_public_key(key_data.encode())


def _rsa2_sign(private_key, content: str) -> str:
    """RSA2(SHA256withRSA) 签名"""
    signature = private_key.sign(
        content.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _rsa2_verify(public_key, content: str, sign: str) -> bool:
    """RSA2 验签"""
    try:
        public_key.verify(
            base64.b64decode(sign),
            content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def _build_sign_content(params: dict) -> str:
    """
    构建待签名字符串

    规则：参数按 key 字母序排列，排除 sign 和 sign_type，
    用 & 连接 key=value 对
    """
    filtered = {
        k: v for k, v in params.items()
        if v is not None and v != "" and k not in ("sign", "sign_type")
    }
    sorted_items = sorted(filtered.items())
    return "&".join(f"{k}={v}" for k, v in sorted_items)


class AlipayClient(PaymentGateway):
    """支付宝官方 API 客户端"""

    def __init__(
        self,
        app_id: str,
        private_key_str: str,
        public_key_str: str,
        gateway: str = "https://openapi.alipay.com/gateway.do",
        notify_url: str = "",
    ):
        self.app_id = app_id
        self._private_key = _load_private_key(private_key_str)
        self._public_key = _load_public_key(public_key_str)
        self.gateway = gateway
        self.notify_url = notify_url

    def _build_common_params(self, method: str) -> dict:
        """构建公共请求参数"""
        return {
            "app_id": self.app_id,
            "method": method,
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
        }

    def _sign_params(self, params: dict) -> dict:
        """对参数进行签名"""
        content = _build_sign_content(params)
        params["sign"] = _rsa2_sign(self._private_key, content)
        return params

    async def _request(self, method: str, biz_content: dict) -> dict:
        """发送请求到支付宝网关"""
        params = self._build_common_params(method)
        params["biz_content"] = json.dumps(biz_content, ensure_ascii=False)

        self._sign_params(params)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.gateway, data=params)
            resp.raise_for_status()
            result = resp.json()

        # 支付宝响应字段名：method 中的 . 替换为 _，加 _response 后缀
        response_key = method.replace(".", "_") + "_response"
        response_data = result.get(response_key, {})

        if response_data.get("code") != "10000":
            sub_msg = response_data.get("sub_msg") or response_data.get("msg", "未知错误")
            raise RuntimeError(f"支付宝 API 错误 [{method}]: {sub_msg}")

        return response_data

    async def create_native_pay(
        self,
        out_trade_no: str,
        total_amount: str,
        subject: str,
        notify_url: str,
    ) -> dict:
        """创建当面付扫码支付订单"""
        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "subject": subject,
            "timeout_express": "2h",
        }

        params = self._build_common_params("alipay.trade.precreate")
        params["notify_url"] = notify_url or self.notify_url
        params["biz_content"] = json.dumps(biz_content, ensure_ascii=False)

        self._sign_params(params)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.gateway, data=params)
            resp.raise_for_status()
            result = resp.json()

        response_data = result.get("alipay_trade_precreate_response", {})
        if response_data.get("code") != "10000":
            sub_msg = response_data.get("sub_msg") or response_data.get("msg", "未知错误")
            raise RuntimeError(f"支付宝预创建订单失败: {sub_msg}")

        qr_code = response_data.get("qr_code", "")
        logger.info(f"Alipay precreate success: out_trade_no={out_trade_no}")

        return {"qr_code": qr_code}

    async def create_page_pay(
        self,
        out_trade_no: str,
        total_amount: str,
        subject: str,
        notify_url: str,
        return_url: str,
    ) -> dict:
        """创建电脑网站支付跳转 URL（alipay.trade.page.pay）"""
        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "subject": subject,
            "product_code": "FAST_INSTANT_TRADE_PAY",
        }
        params = self._build_common_params("alipay.trade.page.pay")
        params["notify_url"] = notify_url or self.notify_url
        params["return_url"] = return_url
        params["biz_content"] = json.dumps(biz_content, ensure_ascii=False)
        self._sign_params(params)
        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))
        pay_url = f"{self.gateway}?{query}"
        logger.info(f"Alipay page pay URL built: out_trade_no={out_trade_no}")
        return {"pay_url": pay_url}

    async def query_order(self, out_trade_no: str) -> dict:
        """查询订单状态"""
        try:
            response_data = await self._request("alipay.trade.query", {
                "out_trade_no": out_trade_no,
            })

            trade_status = response_data.get("trade_status", "")
            paid = trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED")

            return {
                "paid": paid,
                "trade_no": response_data.get("trade_no", ""),
                "amount": response_data.get("total_amount", "0"),
            }
        except Exception as e:
            logger.warning(f"Alipay query order failed: {out_trade_no}, error: {e}")
            return {"paid": False, "trade_no": "", "amount": "0"}

    def verify_notify(self, params: dict) -> bool:
        """验证支付宝异步回调签名"""
        sign = params.get("sign", "")
        if not sign:
            return False

        content = _build_sign_content(params)
        return _rsa2_verify(self._public_key, content, sign)

    async def refund(
        self,
        out_trade_no: str,
        refund_amount: str,
        refund_reason: str,
    ) -> dict:
        """申请退款"""
        try:
            response_data = await self._request("alipay.trade.refund", {
                "out_trade_no": out_trade_no,
                "refund_amount": refund_amount,
                "refund_reason": refund_reason,
            })

            fund_change = response_data.get("fund_change", "N")
            return {
                "success": fund_change == "Y",
                "refund_no": response_data.get("trade_no", ""),
                "message": "退款成功" if fund_change == "Y" else "退款处理中",
            }
        except Exception as e:
            logger.error(f"Alipay refund failed: {out_trade_no}, error: {e}")
            return {"success": False, "refund_no": "", "message": str(e)}


def get_alipay_client() -> Optional[AlipayClient]:
    """从配置创建支付宝客户端实例"""
    from core.config import settings

    app_id = getattr(settings, "alipay_app_id", "")
    private_key = getattr(settings, "alipay_private_key", "")
    public_key = getattr(settings, "alipay_public_key", "")

    if not app_id or not private_key or not public_key:
        logger.warning("支付宝配置未完成（缺少 app_id/private_key/public_key）")
        return None

    sandbox = getattr(settings, "alipay_sandbox", False)
    gateway = (
        getattr(settings, "alipay_sandbox_gateway", "https://openapi-sandbox.dl.alipaydev.com/gateway.do")
        if sandbox
        else getattr(settings, "alipay_gateway", "https://openapi.alipay.com/gateway.do")
    )
    notify_url = getattr(settings, "alipay_notify_url", "")

    try:
        client = AlipayClient(
            app_id=app_id,
            private_key_str=private_key,
            public_key_str=public_key,
            gateway=gateway,
            notify_url=notify_url,
        )
        logger.info(f"Alipay client initialized: app_id={app_id}, sandbox={sandbox}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Alipay client: {e}")
        return None
