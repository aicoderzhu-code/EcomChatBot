"""
电商平台 API 客户端抽象基类

统一 OAuth 授权流程、Token 刷新、API 签名、错误处理和日志。
各平台只需实现差异化的签名算法和响应解析。
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PlatformAPIError(Exception):
    """平台 API 调用失败"""

    def __init__(self, platform: str, code: str | int, message: str, raw: dict | None = None):
        self.platform = platform
        self.code = code
        self.raw = raw
        super().__init__(f"[{platform}] API 错误: {message} (code={code})")


class BasePlatformClient(ABC):
    """电商平台 API 客户端基类

    子类需要实现:
        - platform_name: 平台名称
        - api_url: API 网关地址
        - sign_request(): 签名算法
        - _build_request_params(): 构建请求参数
        - _parse_response(): 解析响应数据
        - _build_oauth_params(): 构建 OAuth 请求参数
        - _build_message_params(): 构建消息发送参数
        - verify_webhook_signature(): 验证 Webhook 签名
    """

    platform_name: str = ""
    api_url: str = ""
    oauth_url: str = ""
    default_timeout: float = 15.0

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    @abstractmethod
    def sign_request(self, params: dict[str, Any]) -> str:
        """计算请求签名"""
        ...

    @abstractmethod
    def _build_request_params(
        self, method: str, params: dict[str, Any] | None, access_token: str | None
    ) -> dict[str, Any]:
        """构建完整的请求参数（含系统参数和签名）"""
        ...

    @abstractmethod
    def _parse_response(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        """解析 API 响应，提取业务数据。失败时抛出 PlatformAPIError。"""
        ...

    @abstractmethod
    def _build_message_params(self, conversation_id: str, content: str) -> tuple[str, dict]:
        """构建消息发送参数，返回 (method, params)"""
        ...

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """验证 Webhook 签名"""
        ...

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def call_api(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """通用 API 调用（含指数退避重试）"""
        request_params = self._build_request_params(method, params, access_token)

        async with httpx.AsyncClient(timeout=self.default_timeout) as client:
            resp = await client.post(self.api_url, data=request_params)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(method, data)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_message(
        self,
        access_token: str,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        """发送客服消息（含指数退避重试）"""
        method, params = self._build_message_params(conversation_id, content)
        return await self.call_api(method=method, params=params, access_token=access_token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _oauth_request(self, url: str, params: dict) -> dict:
        """OAuth HTTP 请求（含指数退避重试）"""
        async with httpx.AsyncClient(timeout=self.default_timeout) as client:
            resp = await client.post(url, data=params)
            resp.raise_for_status()
            return resp.json()

    async def get_access_token(self, code: str) -> dict:
        """用授权码换取 access_token"""
        params = {
            "grant_type": "authorization_code",
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "code": code,
            "redirect_uri": "",
        }
        return await self._oauth_request(self.oauth_url, params)

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """刷新 access_token"""
        params = {
            "grant_type": "refresh_token",
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "refresh_token": refresh_token,
        }
        return await self._oauth_request(self.oauth_url, params)
