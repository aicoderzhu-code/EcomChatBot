"""
抖音开放平台 API 客户端
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

DOUYIN_API_URL = "https://open.douyin.com/api"


class DouyinAPIError(Exception):
    """抖音 API 调用失败"""


class DouyinClient:
    """抖音开放平台 API 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    def sign_request(self, params: dict[str, Any]) -> str:
        """
        抖音 API 签名算法

        签名规则：将所有参数按 key 字典序排列，拼接为 key1=value1&key2=value2...
        然后使用 HMAC-SHA256(app_secret, param_string) 生成签名
        """
        sorted_params = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params if k != "sign"])
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            msg=param_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return signature

    async def call_api(
        self,
        endpoint: str,
        params: dict[str, Any],
        access_token: str | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        """通用 API 调用"""
        headers = {
            "Content-Type": "application/json",
        }

        request_params = {
            "app_key": self.app_key,
            "timestamp": str(int(time.time())),
            **params,
        }

        if access_token:
            request_params["access_token"] = access_token

        request_params["sign"] = self.sign_request(request_params)

        url = f"{DOUYIN_API_URL}{endpoint}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == "POST":
                resp = await client.post(url, json=request_params, headers=headers)
            else:
                resp = await client.get(url, params=request_params, headers=headers)
            resp.raise_for_status()
            result = resp.json()

            # 检查业务错误
            if result.get("err_no") != 0:
                raise DouyinAPIError(
                    f"API调用失败: {result.get('err_msg', '')} (code={result.get('err_no', '')})"
                )

            return result.get("data", {})

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, DouyinAPIError)),
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
        return await self.call_api(
            endpoint="/im/message/send",
            params={
                "conversation_id": conversation_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}, ensure_ascii=False),
            },
            access_token=access_token,
        )

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """刷新 access_token"""
        return await self.call_api(
            endpoint="/oauth/refresh_token",
            params={"refresh_token": refresh_token},
        )

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        验证抖音 Webhook 签名

        签名算法：HMAC-SHA256(app_secret, body)，十六进制小写
        """
        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature.lower())

