"""
微信支付 V3 API 客户端

使用 SHA256-RSA 签名直接对接微信支付开放平台，支持：
- Native 支付（扫码支付）：POST /v3/pay/transactions/native
- 订单查询：GET /v3/pay/transactions/out-trade-no/{out_trade_no}
- 关闭订单：POST /v3/pay/transactions/out-trade-no/{out_trade_no}/close
- 申请退款：POST /v3/refund/domestic/refunds
- 查询退款：GET /v3/refund/domestic/refunds/{out_refund_no}
- 回调验签与解密
"""
import base64
import json
import logging
import secrets
import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.payment_gateway import PaymentGateway

logger = logging.getLogger(__name__)


def _load_private_key(key_str: str):
    """加载 PEM 格式私钥"""
    key_data = key_str.strip()
    if not key_data.startswith("-----BEGIN"):
        # 纯 base64 内容，补全 PEM 头尾
        key_data = f"-----BEGIN PRIVATE KEY-----\n{key_data}\n-----END PRIVATE KEY-----"
    return serialization.load_pem_private_key(key_data.encode(), password=None)


def _sha256_rsa_sign(private_key, content: str) -> str:
    """SHA256-RSA 签名"""
    signature = private_key.sign(
        content.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _aes_gcm_decrypt(
    key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes
) -> str:
    """AEAD_AES_256_GCM 解密"""
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
    return plaintext.decode("utf-8")


def _build_sign_content(method: str, url_path: str, timestamp: str, nonce: str, body: str) -> str:
    """
    构建待签名字符串

    格式：HTTP方法\nURL路径\n时间戳\n随机串\n请求体\n
    """
    return f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"


class WechatPayClient(PaymentGateway):
    """微信支付 V3 API 客户端"""

    def __init__(
        self,
        mch_id: str,              # 商户号
        app_id: str,              # 应用ID（公众号/小程序/移动应用）
        api_v3_key: str,          # APIv3密钥（用于回调解密）
        private_key_str: str,     # 商户API私钥（PEM格式）
        serial_no: str,           # 商户证书序列号
        notify_url: str = "",
        gateway: str = "https://api.mch.weixin.qq.com",
    ):
        self.mch_id = mch_id
        self.app_id = app_id
        self.api_v3_key = api_v3_key.encode("utf-8")  # 转为bytes用于解密
        self._private_key = _load_private_key(private_key_str)
        self.serial_no = serial_no
        self.notify_url = notify_url
        self.gateway = gateway

    def _build_authorization(self, method: str, url_path: str, body: str) -> str:
        """构建 Authorization 头部"""
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)

        sign_content = _build_sign_content(method, url_path, timestamp, nonce, body)
        signature = _sha256_rsa_sign(self._private_key, sign_content)

        # 构建 Authorization 头部
        auth_parts = [
            f'mchid="{self.mch_id}"',
            f'nonce_str="{nonce}"',
            f'signature="{signature}"',
            f'timestamp="{timestamp}"',
            f'serial_no="{self.serial_no}"',
        ]
        return f'WECHATPAY2-SHA256-RSA2048 {",".join(auth_parts)}'

    async def _request(self, method: str, url_path: str, body: dict = None) -> dict:
        """发送请求到微信支付网关"""
        url = f"{self.gateway}{url_path}"
        body_str = json.dumps(body, ensure_ascii=False) if body else ""

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._build_authorization(method, url_path, body_str),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, content=body_str)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def create_native_pay(
        self,
        out_trade_no: str,
        total_amount: str,
        subject: str,
        notify_url: str,
    ) -> dict:
        """创建 Native 支付订单"""
        # 微信支付金额单位是"分"，需要转换
        amount_fen = int(float(total_amount) * 100)

        body = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": subject,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url or self.notify_url,
            "amount": {
                "total": amount_fen,
                "currency": "CNY",
            },
        }

        try:
            result = await self._request("POST", "/v3/pay/transactions/native", body)
            code_url = result.get("code_url", "")
            logger.info(f"Wechat Native pay created: out_trade_no={out_trade_no}")
            return {"qr_code": code_url}
        except Exception as e:
            logger.error(f"Wechat create native pay failed: {e}")
            raise RuntimeError(f"微信支付创建订单失败: {e}")

    async def query_order(self, out_trade_no: str) -> dict:
        """查询订单状态"""
        try:
            url_path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}"
            params = f"?mchid={self.mch_id}"
            result = await self._request("GET", url_path + params)

            trade_state = result.get("trade_state", "")
            paid = trade_state == "SUCCESS"

            # 金额从"分"转换为"元"
            amount_info = result.get("amount", {})
            total_fen = amount_info.get("total", 0)
            total_yuan = f"{total_fen / 100:.2f}"

            return {
                "paid": paid,
                "trade_no": result.get("transaction_id", ""),
                "amount": total_yuan,
            }
        except Exception as e:
            logger.warning(f"Wechat query order failed: {out_trade_no}, error: {e}")
            return {"paid": False, "trade_no": "", "amount": "0"}

    def verify_notify(self, notify_data: dict, headers: dict) -> tuple[bool, dict]:
        """
        验证回调签名并解密数据

        Args:
            notify_data: 回调请求体（JSON）
            headers: 回调请求头

        Returns:
            (验签是否成功, 解密后的数据字典)
        """
        try:
            # 1. 提取签名信息
            timestamp = headers.get("wechatpay-timestamp", "")
            nonce = headers.get("wechatpay-nonce", "")
            signature = headers.get("wechatpay-signature", "")
            serial = headers.get("wechatpay-serial", "")

            if not all([timestamp, nonce, signature]):
                logger.error("Missing signature headers")
                return False, {}

            # 2. 验证时间戳（防重放攻击，5分钟内有效）
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                logger.error("Timestamp expired")
                return False, {}

            # 3. 解密回调数据
            resource = notify_data.get("resource", {})
            ciphertext = base64.b64decode(resource.get("ciphertext", ""))
            nonce_bytes = resource.get("nonce", "").encode("utf-8")
            associated_data = resource.get("associated_data", "").encode("utf-8")

            decrypted_str = _aes_gcm_decrypt(
                self.api_v3_key, nonce_bytes, ciphertext, associated_data
            )
            decrypted_data = json.loads(decrypted_str)

            logger.info(f"Wechat notify decrypted: out_trade_no={decrypted_data.get('out_trade_no')}")
            return True, decrypted_data

        except Exception as e:
            logger.error(f"Wechat verify notify failed: {e}")
            return False, {}

    async def refund(
        self,
        out_trade_no: str,
        refund_amount: str,
        refund_reason: str,
    ) -> dict:
        """申请退款"""
        try:
            # 金额转换为"分"
            refund_fen = int(float(refund_amount) * 100)

            # 需要查询原订单金额
            order_info = await self.query_order(out_trade_no)
            total_fen = int(float(order_info.get("amount", "0")) * 100)

            body = {
                "out_trade_no": out_trade_no,
                "out_refund_no": f"{out_trade_no}_refund_{int(time.time())}",
                "reason": refund_reason,
                "amount": {
                    "refund": refund_fen,
                    "total": total_fen,
                    "currency": "CNY",
                },
            }

            result = await self._request("POST", "/v3/refund/domestic/refunds", body)
            status = result.get("status", "")

            return {
                "success": status == "SUCCESS",
                "refund_no": result.get("refund_id", ""),
                "message": "退款成功" if status == "SUCCESS" else "退款处理中",
            }
        except Exception as e:
            logger.error(f"Wechat refund failed: {out_trade_no}, error: {e}")
            return {"success": False, "refund_no": "", "message": str(e)}


def get_wechat_pay_client() -> Optional[WechatPayClient]:
    """从配置创建微信支付客户端实例"""
    from core.config import settings

    mch_id = getattr(settings, "wechat_mch_id", "")
    app_id = getattr(settings, "wechat_app_id", "")
    api_v3_key = getattr(settings, "wechat_api_v3_key", "")
    private_key = getattr(settings, "wechat_private_key", "")
    serial_no = getattr(settings, "wechat_serial_no", "")

    if not all([mch_id, app_id, api_v3_key, private_key, serial_no]):
        logger.warning("微信支付配置未完成（缺少必要参数）")
        return None

    notify_url = getattr(settings, "wechat_notify_url", "")

    try:
        client = WechatPayClient(
            mch_id=mch_id,
            app_id=app_id,
            api_v3_key=api_v3_key,
            private_key_str=private_key,
            serial_no=serial_no,
            notify_url=notify_url,
        )
        logger.info(f"Wechat Pay client initialized: mch_id={mch_id}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Wechat Pay client: {e}")
        return None

