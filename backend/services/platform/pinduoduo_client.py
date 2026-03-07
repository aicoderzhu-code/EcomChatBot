"""
拼多多开放平台 API 客户端
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

PDD_API_URL = "https://gw-api.pinduoduo.com/api/router"


class PinduoduoAPIError(Exception):
    """拼多多 API 调用失败"""


class PinduoduoClient:
    """拼多多 POP API 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    def sign_request(self, params: dict[str, Any]) -> str:
        """
        POP API MD5 签名

        签名规则：将所有参数按 key 字典序排列，拼接 app_secret + key1value1key2value2... + app_secret，
        然后对整个字符串做 MD5 并转大写。
        """
        sorted_params = sorted(params.items())
        sign_str = self.app_secret
        for k, v in sorted_params:
            sign_str += f"{k}{v}"
        sign_str += self.app_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def call_api(
        self,
        method: str,
        params: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """通用 POP API 调用（含指数退避重试）"""
        request_params: dict[str, Any] = {
            "type": method,
            "client_id": self.app_key,
            "timestamp": str(int(time.time() * 1000)),
            "data_type": "JSON",
            "version": "V1",
        }
        if access_token:
            request_params["access_token"] = access_token
        request_params.update(params)

        request_params["sign"] = self.sign_request(request_params)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(PDD_API_URL, data=request_params)
            resp.raise_for_status()
            return resp.json()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, PinduoduoAPIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_message(
        self,
        access_token: str,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        """向买家发送消息（失败自动重试 3 次，指数退避 2-10s）"""
        result = await self.call_api(
            method="pdd.im.message.send",
            params={
                "conversation_id": conversation_id,
                "msg_type": 1,  # 文本消息
                "content": json.dumps({"text": content}, ensure_ascii=False),
            },
            access_token=access_token,
        )
        if "error_response" in result:
            err = result["error_response"]
            raise PinduoduoAPIError(
                f"发送消息失败: {err.get('error_msg', '')} (code={err.get('error_code', '')})"
            )
        return result

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """刷新 access_token"""
        return await self.call_api(
            method="pdd.pop.auth.token.refresh",
            params={"refresh_token": refresh_token},
        )

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        验证拼多多 Webhook 签名

        签名算法：HMAC-SHA256(app_secret, body)，十六进制小写
        """
        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature.lower())
