"""快手开放平台 API 客户端"""
import hashlib
import hmac
import json
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

KS_API_URL = "https://open.kuaishou.com/openapi"


class KuaishouClient:
    """快手开放平台 API 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    def sign_request(self, params: dict) -> str:
        """SHA256 签名

        签名算法：app_secret + key1value1key2value2... + app_secret，SHA256 hex
        """
        sorted_params = sorted(params.items())
        sign_str = self.app_secret
        for k, v in sorted_params:
            if v is not None:
                sign_str += f"{k}{v}"
        sign_str += self.app_secret
        return hashlib.sha256(sign_str.encode("utf-8")).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def call_api(
        self, method: str, params: dict | None = None, access_token: str | None = None
    ) -> dict:
        """调用快手开放平台 API（含指数退避重试）"""
        sys_params = {
            "appkey": self.app_key,
            "method": method,
            "timestamp": str(int(time.time() * 1000)),
            "version": "1",
            "signMethod": "SHA256",
        }
        if access_token:
            sys_params["access_token"] = access_token
        if params:
            sys_params["param_json"] = json.dumps(params, ensure_ascii=False)

        sys_params["sign"] = self.sign_request(sys_params)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{KS_API_URL}/{method}", json=sys_params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("result") != 1 and data.get("code") != 0:
            raise Exception(
                f"快手 API 错误: {data.get('error_code', data.get('code'))} - {data.get('error_msg', data.get('msg', ''))}"
            )

        return data.get("data", data)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_access_token(self, code: str) -> dict:
        """用授权码换取 access_token（含指数退避重试）"""
        url = "https://open.kuaishou.com/oauth2/access_token"
        params = {
            "grant_type": "authorization_code",
            "app_id": self.app_key,
            "app_secret": self.app_secret,
            "code": code,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=params)
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """刷新 access_token（含指数退避重试）"""
        url = "https://open.kuaishou.com/oauth2/refresh_token"
        params = {
            "grant_type": "refresh_token",
            "app_id": self.app_key,
            "app_secret": self.app_secret,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=params)
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_message(self, access_token: str, buyer_id: str, content: str) -> dict:
        """发送客服消息"""
        return await self.call_api(
            method="open.seller.im.send",
            params={
                "buyer_open_id": buyer_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}),
            },
            access_token=access_token,
        )

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """验证快手消息推送签名"""
        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected.lower(), signature.lower())
