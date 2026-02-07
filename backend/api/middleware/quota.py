"""
配额检查中间件和装饰器
"""
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Any
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from services.quota_service import QuotaService


class QuotaType(Enum):
    """配额类型"""
    CONVERSATION = "conversation"      # 对话次数(月)
    API_CALL = "api_call"              # API调用次数(月)
    STORAGE = "storage"                # 存储空间(GB)
    CONCURRENT = "concurrent"          # 并发会话数
    KNOWLEDGE_ITEMS = "knowledge"      # 知识库条目数


class OverLimitStrategy(Enum):
    """超限处理策略"""
    REJECT = "reject"                  # 拒绝服务
    UPGRADE_PROMPT = "upgrade_prompt"  # 提示升级
    PAY_AS_YOU_GO = "pay_as_you_go"    # 按量付费


@dataclass
class QuotaCheckResult:
    """配额检查结果"""
    allowed: bool
    quota_type: QuotaType
    used: int
    limit: int
    remaining: int
    strategy: Optional[OverLimitStrategy] = None
    message: Optional[str] = None


def check_quota(
    quota_type: QuotaType,
    amount: int = 1,
    get_amount: Optional[Callable] = None
):
    """
    配额检查装饰器

    用法示例:
        @router.post("/conversation/create")
        @check_quota(QuotaType.CONVERSATION)
        async def create_conversation(...):
            pass

        # 动态数量
        @router.post("/knowledge/batch-import")
        @check_quota(QuotaType.KNOWLEDGE_ITEMS, get_amount=lambda req: len(req.items))
        async def batch_import(...):
            pass

    Args:
        quota_type: 配额类型
        amount: 固定消耗数量
        get_amount: 动态获取消耗数量的函数
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取 request 对象
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="无法获取请求对象"
                )

            # 获取 tenant_id
            tenant_id = getattr(request.state, "tenant_id", None)
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证或租户ID缺失"
                )

            # 计算实际消耗数量
            actual_amount = amount
            if get_amount:
                # 从请求体或参数中获取
                body = kwargs.get("request_body") or kwargs.get("body") or kwargs.get("data")
                if body:
                    try:
                        actual_amount = get_amount(body)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"计算配额消耗数量失败: {str(e)}"
                        )

            # 获取配额服务(从依赖注入)
            from db import get_async_session

            quota_service: Optional[QuotaService] = None
            async with get_async_session() as db:
                quota_service = QuotaService(db)

            # 执行配额检查
            try:
                # 根据不同配额类型调用对应的检查方法
                if quota_type == QuotaType.CONVERSATION:
                    await quota_service.check_conversation_quota(tenant_id)
                elif quota_type == QuotaType.API_CALL:
                    await quota_service.check_api_quota(tenant_id)
                elif quota_type == QuotaType.STORAGE:
                    await quota_service.check_storage_quota(tenant_id, actual_amount)
                elif quota_type == QuotaType.CONCURRENT:
                    # 并发检查需要特殊处理
                    concurrent_manager = getattr(request.app.state, "concurrent_quota_manager", None)
                    if concurrent_manager:
                        # 会在函数执行前检查,执行后释放
                        pass
                else:
                    # 其他类型暂不支持
                    pass

            except Exception as e:
                # 处理配额超限异常
                from core.exceptions import QuotaExceededException
                if isinstance(e, QuotaExceededException):
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={
                            "code": "QUOTA_EXCEEDED",
                            "message": str(e),
                            "quota_type": quota_type.value,
                            "upgrade_url": "/pricing"
                        }
                    )
                raise

            # 执行原函数
            result = await func(*args, **kwargs)

            return result

        return wrapper
    return decorator


class ConcurrentQuotaManager:
    """并发配额管理器"""

    def __init__(self, redis: Redis, quota_service: QuotaService):
        self.redis = redis
        self.quota_service = quota_service

    async def acquire(self, tenant_id: str, conversation_id: str) -> bool:
        """
        获取并发槽位

        Args:
            tenant_id: 租户ID
            conversation_id: 会话ID

        Returns:
            bool: 是否成功获取槽位
        """
        key = f"concurrent:{tenant_id}"

        # 获取订阅信息获取并发限制
        from services.subscription_service import SubscriptionService
        from db import get_async_session

        async with get_async_session() as db:
            subscription_service = SubscriptionService(db)
            subscription = await subscription_service.get_subscription(tenant_id)
            concurrent_limit = subscription.concurrent_quota

        # 检查当前并发数
        current_count = await self.redis.scard(key)

        if current_count >= concurrent_limit:
            return False

        # 添加会话到活跃集合
        await self.redis.sadd(key, conversation_id)
        # 设置过期时间(24小时,安全机制)
        await self.redis.expire(key, 86400)

        return True

    async def release(self, tenant_id: str, conversation_id: str):
        """
        释放并发槽位

        Args:
            tenant_id: 租户ID
            conversation_id: 会话ID
        """
        key = f"concurrent:{tenant_id}"
        await self.redis.srem(key, conversation_id)

    async def get_active_count(self, tenant_id: str) -> int:
        """
        获取当前活跃会话数

        Args:
            tenant_id: 租户ID

        Returns:
            int: 活跃会话数
        """
        key = f"concurrent:{tenant_id}"
        count = await self.redis.scard(key)
        return count or 0

    async def get_active_conversations(self, tenant_id: str) -> set[str]:
        """
        获取所有活跃会话ID

        Args:
            tenant_id: 租户ID

        Returns:
            set[str]: 活跃会话ID集合
        """
        key = f"concurrent:{tenant_id}"
        members = await self.redis.smembers(key)
        return {m.decode() if isinstance(m, bytes) else m for m in members}

    async def cleanup_expired(self, tenant_id: str, active_conversation_ids: set[str]):
        """
        清理已过期的会话

        Args:
            tenant_id: 租户ID
            active_conversation_ids: 当前实际活跃的会话ID集合
        """
        key = f"concurrent:{tenant_id}"
        cached_conversations = await self.get_active_conversations(tenant_id)

        # 找出不再活跃的会话
        expired = cached_conversations - active_conversation_ids

        if expired:
            await self.redis.srem(key, *expired)


def check_concurrent_quota(conversation_id_key: str = "conversation_id"):
    """
    并发配额检查装饰器

    用法:
        @router.post("/conversation/message")
        @check_concurrent_quota("conversation_id")
        async def send_message(conversation_id: str, ...):
            pass

    Args:
        conversation_id_key: 从参数中获取conversation_id的键名
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取 request 和 conversation_id
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            conversation_id = kwargs.get(conversation_id_key)
            if not conversation_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"缺少参数: {conversation_id_key}"
                )

            tenant_id = getattr(request.state, "tenant_id", None)
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证"
                )

            # 获取并发管理器
            concurrent_manager: Optional[ConcurrentQuotaManager] = getattr(
                request.app.state, "concurrent_quota_manager", None
            )

            if not concurrent_manager:
                # 如果没有配置并发管理器,直接执行
                return await func(*args, **kwargs)

            # 尝试获取并发槽位
            acquired = await concurrent_manager.acquire(tenant_id, conversation_id)

            if not acquired:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "CONCURRENT_LIMIT_EXCEEDED",
                        "message": "并发会话数已达上限,请稍后重试或升级套餐"
                    }
                )

            try:
                # 执行原函数
                result = await func(*args, **kwargs)
                return result
            finally:
                # 释放槽位(在实际场景中可能需要在会话结束时调用)
                # 这里仅作为示例,实际可能需要在WebSocket断开或其他地方调用
                pass

        return wrapper
    return decorator