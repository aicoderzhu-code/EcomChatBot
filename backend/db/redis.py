"""
Redis 连接管理
"""
import json
from typing import Any

import redis.asyncio as redis

from core.config import settings

# Redis 客户端实例
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端"""
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(
            settings.redis_url_str,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )
    return redis_client


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


class RedisCache:
    """Redis 缓存封装"""

    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client

    async def get(self, key: str) -> Any | None:
        """获取缓存"""
        value = await self.client.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int | None = None,
    ) -> None:
        """设置缓存"""
        serialized = json.dumps(value, ensure_ascii=False)
        if expire:
            await self.client.setex(key, expire, serialized)
        else:
            await self.client.set(key, serialized)

    async def delete(self, key: str) -> None:
        """删除缓存"""
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return bool(await self.client.exists(key))

    async def expire(self, key: str, seconds: int) -> None:
        """设置过期时间"""
        await self.client.expire(key, seconds)

    async def incr(self, key: str, amount: int = 1) -> int:
        """递增"""
        return await self.client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """递减"""
        return await self.client.decrby(key, amount)

    async def hget(self, name: str, key: str) -> Any | None:
        """获取哈希字段"""
        value = await self.client.hget(name, key)
        if value:
            return json.loads(value)
        return None

    async def hset(self, name: str, key: str, value: Any) -> None:
        """设置哈希字段"""
        serialized = json.dumps(value, ensure_ascii=False)
        await self.client.hset(name, key, serialized)

    async def hgetall(self, name: str) -> dict[str, Any]:
        """获取所有哈希字段"""
        data = await self.client.hgetall(name)
        return {k: json.loads(v) for k, v in data.items()}

    async def lpush(self, key: str, *values: Any) -> int:
        """列表左侧推入"""
        serialized_values = [json.dumps(v, ensure_ascii=False) for v in values]
        return await self.client.lpush(key, *serialized_values)

    async def rpush(self, key: str, *values: Any) -> int:
        """列表右侧推入"""
        serialized_values = [json.dumps(v, ensure_ascii=False) for v in values]
        return await self.client.rpush(key, *serialized_values)

    async def lrange(self, key: str, start: int, end: int) -> list[Any]:
        """获取列表范围"""
        values = await self.client.lrange(key, start, end)
        return [json.loads(v) for v in values]

    async def llen(self, key: str) -> int:
        """获取列表长度"""
        return await self.client.llen(key)


async def get_cache() -> RedisCache:
    """获取 Redis 缓存实例"""
    client = await get_redis()
    return RedisCache(client)
