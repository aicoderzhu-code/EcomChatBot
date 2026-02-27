"""
请求追踪中间件 - 添加请求ID和日志
"""
import uuid
import time
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.datastructures import MutableHeaders

from utils.logger import request_logger


class RequestLoggingMiddleware:
    """请求日志中间件（纯 ASGI，兼容 StreamingResponse）"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_id = str(uuid.uuid4())
        scope["state"] = scope.get("state", {})
        request.state.request_id = request_id

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        tenant_id = getattr(request.state, "tenant_id", None)
        start_time = time.time()

        request_logger.log_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            tenant_id=tenant_id,
            ip=client_ip,
            user_agent=user_agent,
        )

        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start_time) * 1000
            request_logger.log_response(
                request_id=request_id,
                status_code=status_code,
                duration_ms=duration_ms,
            )

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
