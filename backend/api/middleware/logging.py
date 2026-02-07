"""
请求追踪中间件 - 添加请求ID和日志
"""
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.logger import request_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 获取租户ID（如果有）
        tenant_id = getattr(request.state, "tenant_id", None)

        # 记录请求开始
        start_time = time.time()

        request_logger.log_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            tenant_id=tenant_id,
            ip=client_ip,
            user_agent=user_agent,
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 记录请求结束
            duration_ms = (time.time() - start_time) * 1000

            request_logger.log_response(
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
                response_size=int(response.headers.get("content-length", 0)),
            )

            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 记录错误
            request_logger.log_error(request_id=request_id, error=e)
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
