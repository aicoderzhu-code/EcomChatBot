"""淘宝 TOP API 客户端"""
import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

TOP_API_URL = "https://eco.taobao.com/router/rest"


class TaobaoClient:
    """淘宝 TOP (Taobao Open Platform) API 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    def sign_request(self, params: dict) -> str:
        """MD5 签名

        签名算法：
        1. 参数按 key 字典序排列
        2. 拼接为 key1value1key2value2...
        3. 前后加 app_secret
        4. MD5 取大写 hex
        """
        sorted_params = sorted(params.items())
        sign_str = self.app_secret
        for k, v in sorted_params:
            if v is not None:
                sign_str += f"{k}{v}"
        sign_str += self.app_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def call_api(
        self, method: str, params: dict | None = None, session_key: str | None = None
    ) -> dict:
        """调用淘宝 TOP API（含指数退避重试）"""
        sys_params = {
            "app_key": self.app_key,
            "method": method,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
        }
        if session_key:
            sys_params["session"] = session_key
        if params:
            sys_params.update(params)

        sys_params["sign"] = self.sign_request(sys_params)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TOP_API_URL, data=sys_params)
            resp.raise_for_status()
            data = resp.json()

        # 淘宝 API 错误处理
        if "error_response" in data:
            err = data["error_response"]
            raise Exception(f"淘宝 API 错误: {err.get('code')} - {err.get('msg')}")

        # 响应格式: {"method_response": {...}}
        response_key = method.replace(".", "_") + "_response"
        return data.get(response_key, data)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_access_token(self, code: str) -> dict:
        """用授权码换取 access_token（含指数退避重试）"""
        url = "https://oauth.taobao.com/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "code": code,
            "redirect_uri": "",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=params)
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """刷新 access_token（含指数退避重试）"""
        url = "https://oauth.taobao.com/token"
        params = {
            "grant_type": "refresh_token",
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=params)
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_message(self, session_key: str, buyer_nick: str, content: str) -> dict:
        """发送客服消息"""
        return await self.call_api(
            method="taobao.miniapp.message.send",
            params={
                "target_user_nick": buyer_nick,
                "msg_type": "text",
                "content": json.dumps({"text": content}),
            },
            session_key=session_key,
        )

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """验证淘宝消息推送签名"""
        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            body,
            hashlib.md5,
        ).hexdigest().upper()
        return hmac.compare_digest(expected, signature.upper())
