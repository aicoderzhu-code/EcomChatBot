"""
限流中间件 - 使用滑动窗口算法
"""
import time
import json
from typing import Optional, Tuple
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.datastructures import MutableHeaders
import redis.asyncio as redis

from core.config import settings


class RateLimitConfig:
    """限流配置"""

    # 用户维度限流
    USER_LIMIT = 60  # 每分钟60次
    USER_WINDOW = 60  # 窗口60秒

    # IP维度限流
    IP_LIMIT = 100  # 每分钟100次
    IP_WINDOW = 60  # 窗口60秒

    # 全局维度限流
    GLOBAL_LIMIT = 10000  # 每秒10000次
    GLOBAL_WINDOW = 1  # 窗口1秒

    # API维度限流(特定API的限制)
    API_LIMITS = {
        "/api/v1/conversation/chat": (30, 60),  # 每分钟30次
        "/api/v1/ai/chat": (20, 60),  # 每分钟20次
        "/api/v1/knowledge/batch-import": (5, 60),  # 每分钟5次
        "/api/v1/conversation/send": (30, 60),  # 每分钟30次
    }


class SlidingWindowRateLimiter:
    """滑动窗口限流器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, int, int]:
        """
        检查是否允许请求

        使用Redis的滑动窗口算法

        Returns:
            (allowed, remaining, reset_after)
        """
        now = time.time()
        window_start = now - window

        # Redis管道操作
        pipe = self.redis.pipeline()

        # 移除窗口外的请求记录
        pipe.zremrangebyscore(key, 0, window_start)

        # 获取当前窗口内的请求数
        pipe.zcard(key)

        # 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 设置过期时间
        pipe.expire(key, window)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # 超出限制，需要移除刚才添加的记录
            await self.redis.zrem(key, str(now))

            # 计算重试时间
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_after = int(oldest[0][1] + window - now)
            else:
                reset_after = window

            return False, 0, reset_after

        remaining = limit - current_count - 1
        return True, remaining, window


class RateLimitMiddleware:
    """限流中间件（纯 ASGI，兼容 StreamingResponse）"""

    # 白名单路径
    WHITELIST_PATHS = [
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
        "/",
    ]

    def __init__(self, app: ASGIApp, redis_client: redis.Redis):
        self.app = app
        self.limiter = SlidingWindowRateLimiter(redis_client)
        self.config = RateLimitConfig()
        self.redis = redis_client

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # 检查白名单
        if self._is_whitelisted(request.url.path):
            await self.app(scope, receive, send)
            return

        tenant_id = getattr(request.state, "tenant_id", None)
        client_ip = self._get_client_ip(request)

        # 1. 全局限流
        global_allowed, _, _ = await self.limiter.is_allowed(
            "ratelimit:global", self.config.GLOBAL_LIMIT, self.config.GLOBAL_WINDOW
        )
        if not global_allowed:
            await self._send_rate_limit_response(send, "服务繁忙,请稍后重试", 1)
            return

        # 2. IP 限流
        ip_key = f"ratelimit:ip:{client_ip}"
        ip_allowed, ip_remaining, ip_reset = await self.limiter.is_allowed(
            ip_key, self.config.IP_LIMIT, self.config.IP_WINDOW
        )
        if not ip_allowed:
            await self._send_rate_limit_response(send, "请求过于频繁,请稍后重试", ip_reset)
            return

        # 3. 租户限流
        user_remaining = ip_remaining
        user_reset = ip_reset
        if tenant_id:
            override = await self._get_rate_limit_override(tenant_id)
            user_limit = (
                int(self.config.USER_LIMIT * override)
                if override
                else self.config.USER_LIMIT
            )
            user_key = f"ratelimit:tenant:{tenant_id}"
            user_allowed, user_remaining, user_reset = await self.limiter.is_allowed(
                user_key, user_limit, self.config.USER_WINDOW
            )
            if not user_allowed:
                await self._send_rate_limit_response(send, "API调用频率超限", user_reset)
                return

        # 4. API 特定限流
        api_limit = self.config.API_LIMITS.get(request.url.path)
        if api_limit:
            api_key = f"ratelimit:api:{tenant_id or client_ip}:{request.url.path}"
            api_allowed, _, api_reset = await self.limiter.is_allowed(
                api_key, api_limit[0], api_limit[1]
            )
            if not api_allowed:
                await self._send_rate_limit_response(send, "该接口调用频率超限", api_reset)
                return

        # 注入限流头
        rl_limit = str(self.config.USER_LIMIT)
        rl_remaining = str(user_remaining)
        rl_reset = str(int(time.time()) + user_reset)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-RateLimit-Limit"] = rl_limit
                headers["X-RateLimit-Remaining"] = rl_remaining
                headers["X-RateLimit-Reset"] = rl_reset
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _is_whitelisted(self, path: str) -> bool:
        return any(path.startswith(wp) for wp in self.WHITELIST_PATHS)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def _get_rate_limit_override(self, tenant_id: str) -> Optional[float]:
        try:
            override = await self.redis.get(f"rate_limit_override:{tenant_id}")
            return float(override) if override else None
        except Exception:
            return None

    async def _send_rate_limit_response(self, send: Send, message: str, retry_after: int):
        body = json.dumps({
            "success": False,
            "error": {"code": "RATE_LIMIT_EXCEEDED", "message": message},
            "retry_after": retry_after,
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(retry_after).encode()),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
