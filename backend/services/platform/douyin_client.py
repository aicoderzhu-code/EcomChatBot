"""抖店开放平台 API 客户端（openapi-fxg 协议）"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

DOUYIN_API_URL = "https://openapi-fxg.jinritemai.com"


class DouyinAPIError(Exception):
    """抖店 API 调用失败"""


class DouyinClient:
    """抖店开放平台 API 客户端"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = DOUYIN_API_URL

    @staticmethod
    def _normalize_param_json(params: dict[str, Any] | str) -> str:
        """将业务参数转换为稳定字符串，避免签名抖动。"""
        if isinstance(params, str):
            return params
        return json.dumps(params or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def sign_request(
        self,
        params: dict[str, Any],
        sign_method: str = "hmac-sha256",
    ) -> str:
        """
        抖店签名算法。

        官方推荐参数顺序：app_key, method, param_json, timestamp, v。
        access_token、sign、sign_method 不参与签名。
        """
        order = ["app_key", "method", "param_json", "timestamp", "v"]
        sign_parts: list[str] = []

        for key in order:
            if params.get(key) is not None:
                sign_parts.append(f"{key}{params[key]}")

        # 兼容后续新增可签名字段
        for key in sorted(params.keys()):
            if key in order or key in {"access_token", "sign", "sign_method"}:
                continue
            if params.get(key) is not None:
                sign_parts.append(f"{key}{params[key]}")

        sign_source = f"{self.app_secret}{''.join(sign_parts)}{self.app_secret}"
        algo = (sign_method or "md5").lower()
        if algo == "hmac-sha256":
            return hmac.new(
                self.app_secret.encode("utf-8"),
                msg=sign_source.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        return hashlib.md5(sign_source.encode("utf-8")).hexdigest()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def call_api(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        access_token: str | None = None,
        api_method: str | None = None,
        sign_method: str = "hmac-sha256",
        api_version: str = "2",
    ) -> dict[str, Any]:
        """通用 API 调用（含指数退避重试）。"""
        biz_params = params or {}
        param_json = self._normalize_param_json(biz_params)
        method_name = api_method or endpoint.strip("/").replace("/", ".")

        sign_params: dict[str, Any] = {
            "app_key": self.app_key,
            "method": method_name,
            "param_json": param_json,
            "timestamp": str(int(time.time())),
            "v": api_version,
            "sign_method": sign_method,
        }
        if access_token:
            sign_params["access_token"] = access_token

        sign = self.sign_request(sign_params, sign_method=sign_method)

        query_params = {
            "method": method_name,
            "app_key": self.app_key,
            "timestamp": sign_params["timestamp"],
            "v": api_version,
            "sign": sign,
            "sign_method": sign_method,
        }
        if access_token:
            query_params["access_token"] = access_token

        url = f"{self.base_url}{endpoint}"
        body = {"param_json": param_json}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                params=query_params,
                json=body,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()

        # 抖店成功码为 10000
        code = int(result.get("code", 0) or 0)
        if code != 10000:
            raise DouyinAPIError(
                f"API调用失败: {result.get('msg', '')} "
                f"(code={result.get('code', '')}, sub_code={result.get('sub_code', '')}, sub_msg={result.get('sub_msg', '')})"
            )
        return result.get("data", {}) or {}

    async def create_access_token(
        self,
        code: str = "",
        grant_type: str = "authorization_code",
        shop_id: str | None = None,
        auth_id: str | None = None,
        auth_subject_type: str | None = None,
    ) -> dict[str, Any]:
        """通过 code/shop_id 换取 access_token。"""
        params: dict[str, Any] = {
            "grant_type": grant_type,
            "code": code,
        }
        if shop_id:
            params["shop_id"] = shop_id
        if auth_id:
            params["auth_id"] = auth_id
        if auth_subject_type:
            params["auth_subject_type"] = auth_subject_type
        return await self.call_api(
            endpoint="/token/create",
            params=params,
            api_method="token.create",
            sign_method="hmac-sha256",
        )

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """刷新 access_token。"""
        return await self.call_api(
            endpoint="/token/refresh",
            params={
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            api_method="token.refresh",
            sign_method="hmac-sha256",
        )

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
        """
        发送客服消息。

        该接口在不同应用形态下权限差异较大，使用统一 call_api 流程调用，
        由上层按业务处理失败兜底。
        """
        return await self.call_api(
            endpoint="/im/message/send",
            api_method="im.message.send",
            params={
                "conversation_id": conversation_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}, ensure_ascii=False),
            },
            access_token=access_token,
        )

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        app_id: str | None = None,
        sign_method: str | None = None,
    ) -> bool:
        """
        验证抖店消息推送签名。

        官方文档：event-sign = md5(app_id + body + app_secret)，
        也支持 hmac-sha256 算法。
        """
        if not signature:
            return False

        app_key = app_id or self.app_key
        sign_param = f"{app_key}{body.decode('utf-8', errors='ignore')}{self.app_secret}"
        algo = (sign_method or "md5").lower()

        if algo == "hmac-sha256":
            expected = hmac.new(
                self.app_secret.encode("utf-8"),
                msg=sign_param.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        else:
            expected = hashlib.md5(sign_param.encode("utf-8")).hexdigest()

        return hmac.compare_digest(expected.lower(), signature.lower())
