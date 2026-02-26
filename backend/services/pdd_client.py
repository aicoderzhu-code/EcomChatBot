import hashlib
import json
import time

import httpx

from core.config import settings

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


class PddClient:
    """拼多多开放平台 API 客户端"""

    def __init__(self, app_key: str | None = None, app_secret: str | None = None):
        self.app_key = app_key or settings.pdd_app_key
        self.app_secret = app_secret or settings.pdd_app_secret
        self.base_url = settings.pdd_api_base_url

    def _generate_sign(self, params: dict) -> str:
        """MD5 签名：secret + 排序后的 key+value + secret"""
        sorted_params = sorted(params.items())
        sign_str = self.app_secret
        for k, v in sorted_params:
            sign_str += f"{k}{v}"
        sign_str += self.app_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    def _build_params(self, api_type: str, biz_params: dict) -> dict:
        """构建完整请求参数"""
        params = {
            "type": api_type,
            "client_id": self.app_key,
            "timestamp": str(int(time.time())),
            "data_type": "JSON",
            "version": "V1",
        }
        if biz_params:
            params["data"] = json.dumps(biz_params)
        params["sign"] = self._generate_sign(params)
        return params

    async def _request(self, api_type: str, biz_params: dict) -> dict:
        """发起 HTTP 请求"""
        params = self._build_params(api_type, biz_params)
        resp = await _get_http_client().post(self.base_url, data=params)
        resp.raise_for_status()
        return resp.json()

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        msg_type: int = 1,  # 1=文本
    ) -> bool:
        """发送客服消息给买家"""
        result = await self._request(
            "pdd.service.message.push",
            {
                "conversation_id": conversation_id,
                "msg_type": msg_type,
                "content": content,
            },
        )
        return result.get("result", {}).get("is_success", False)

    async def get_conversation_list(self, page: int = 1, page_size: int = 20) -> list:
        """获取会话列表"""
        result = await self._request(
            "pdd.im.conversation.list.get",
            {"page": page, "page_size": page_size},
        )
        return result.get("result", {}).get("conversation_list", [])
