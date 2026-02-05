"""
安全防护中间件
"""
import time
from typing import Callable
from fastapi import Request, HTTPException, status
from redis import Redis
from core.config import settings


class RateLimiter:
    """速率限制器（基于Redis）"""

    def __init__(self):
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _get_key(self, identifier: str, limit_type: str) -> str:
        """生成Redis键"""
        return f"rate_limit:{limit_type}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        检查速率限制

        Args:
            identifier: 标识符（tenant_id、IP地址等）
            limit_type: 限制类型（api、conversation、knowledge等）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            True表示允许请求，False表示超限
        """
        key = self._get_key(identifier, limit_type)

        try:
            # 获取当前计数
            current = self.redis.get(key)

            if current is None:
                # 首次请求，设置计数
                pipe = self.redis.pipeline()
                pipe.set(key, 1, ex=window_seconds)
                pipe.execute()
                return True

            # 检查是否超限
            if int(current) >= max_requests:
                return False

            # 增加计数
            self.redis.incr(key)
            return True

        except Exception as e:
            # Redis故障时降级，允许请求
            print(f"Rate limiter error: {e}")
            return True

    async def get_remaining_quota(
        self,
        identifier: str,
        limit_type: str
    ) -> int:
        """获取剩余配额"""
        key = self._get_key(identifier, limit_type)
        current = self.redis.get(key)
        return int(current) if current else 0


# 全局限流器实例
rate_limiter = RateLimiter()


async def rate_limit_middleware(
    request: Request,
    call_next: Callable
):
    """
    全局限流中间件

    限制规则：
    - 全局：1000 req/min
    - 单IP：100 req/min
    - 单租户API：基于套餐配额
    """
    # 1. 全局限流
    global_limit_ok = await rate_limiter.check_rate_limit(
        identifier="global",
        limit_type="global",
        max_requests=1000,
        window_seconds=60
    )

    if not global_limit_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="服务繁忙，请稍后再试"
        )

    # 2. IP限流
    client_ip = request.client.host
    ip_limit_ok = await rate_limiter.check_rate_limit(
        identifier=client_ip,
        limit_type="ip",
        max_requests=100,
        window_seconds=60
    )

    if not ip_limit_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )

    # 3. 租户限流（如果有API Key）
    api_key = request.headers.get("X-API-Key")
    if api_key:
        tenant_limit_ok = await rate_limiter.check_rate_limit(
            identifier=api_key,
            limit_type="tenant_api",
            max_requests=10000,  # 应该从套餐配置读取
            window_seconds=3600
        )

        if not tenant_limit_ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API调用次数超限，请升级套餐"
            )

    # 继续处理请求
    response = await call_next(request)

    # 添加限流信息到响应头
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(
        await rate_limiter.get_remaining_quota(client_ip, "ip")
    )

    return response
