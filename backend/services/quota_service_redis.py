"""
增强的配额管理服务 - 使用 Redis Lua 脚本实现原子操作

提供高性能的配额检查和消费功能，支持多种配额类型：
- 对话次数配额 (conversation)
- 并发会话配额 (concurrent)
- 存储空间配额 (storage)
- API 调用配额 (api)
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import QuotaExceededException
from db import get_cache
from models import Subscription, UsageRecord
from services.subscription_service import SubscriptionService


class QuotaType(str, Enum):
    """配额类型"""

    CONVERSATION = "conversation"
    CONCURRENT = "concurrent"
    STORAGE = "storage"
    API = "api"


# ============ Redis Lua 脚本 ============

# 原子检查并消费配额的 Lua 脚本
CHECK_AND_CONSUME_SCRIPT = """
local key = KEYS[1]
local quota = tonumber(ARGV[1])
local amount = tonumber(ARGV[2])
local reset = ARGV[3]

-- 获取当前使用量
local current = tonumber(redis.call('GET', key)) or 0

-- 检查是否超过配额（-1 表示无限制）
if quota ~= -1 and current + amount > quota then
    return {0, current, quota}  -- 不允许，返回当前使用量和配额
end

-- 原子递增使用量
local new_current = redis.call('INCRBY', key, amount)

-- 设置过期时间（每月重置）
if reset ~= "" then
    redis.call('EXPIREAT', key, reset)
end

-- 计算剩余配额
local remaining = quota == -1 and -1 or (quota - new_current)

return {1, new_current, remaining}  -- 允许，返回新使用量和剩余配额
"""

# 获取当前配额使用情况
GET_USAGE_SCRIPT = """
local key = KEYS[1]
local quota = tonumber(ARGV[1])

local current = tonumber(redis.call('GET', key)) or 0
local remaining = quota == -1 and -1 or (quota - current)

return {current, remaining}
"""


class RedisQuotaService:
    """基于 Redis 的配额管理服务"""

    # 套餐配置（与数据库 Subscription 配置保持一致）
    PLAN_QUOTAS = {
        "free": {
            "conversation": 100,  # 100 次对话/月
            "concurrent": 5,  # 5 个并发会话
            "storage": 10,  # 10 GB 存储
            "api": 1000,  # 1000 次 API 调用/月
        },
        "basic": {
            "conversation": 1000,
            "concurrent": 20,
            "storage": 50,
            "api": 10000,
        },
        "professional": {
            "conversation": 10000,
            "concurrent": 100,
            "storage": 200,
            "api": 100000,
        },
        "enterprise": {
            "conversation": -1,  # 无限制
            "concurrent": -1,
            "storage": -1,
            "api": -1,
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_service = SubscriptionService(db)

    async def _get_quota_limit(self, tenant_id: str, quota_type: QuotaType) -> int:
        """获取租户的配额限制"""
        subscription = await self.subscription_service.get_subscription(tenant_id)
        plan_type = subscription.plan_type

        if plan_type not in self.PLAN_QUOTAS:
            raise ValueError(f"未知的套餐类型: {plan_type}")

        return self.PLAN_QUOTAS[plan_type][quota_type.value]

    def _get_quota_key(self, tenant_id: str, quota_type: QuotaType, year: int, month: int) -> str:
        """生成 Redis 配额键"""
        return f"quota:{tenant_id}:{quota_type.value}:{year}:{month}"

    def _get_month_end_timestamp(self) -> int:
        """获取月底时间戳（用于 Redis 过期）"""
        from calendar import monthrange

        now = datetime.utcnow()
        _, last_day = monthrange(now.year, now.month)
        month_end = datetime(now.year, now.month, last_day, 23, 59, 59)
        return int(month_end.timestamp())

    async def check_and_consume(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1,
    ) -> dict[str, Any]:
        """
        检查并消费配额（原子操作）

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型
            amount: 消费数量

        Returns:
            dict: {
                "allowed": bool,  # 是否允许
                "current_usage": int,  # 当前使用量
                "remaining": int,  # 剩余配额（-1 表示无限制）
                "limit": int,  # 配额限制（-1 表示无限制）
            }

        Raises:
            QuotaExceededException: 配额已用完
        """
        cache = await get_cache()
        quota_limit = await self._get_quota_limit(tenant_id, quota_type)

        # 无限制套餐直接通过
        if quota_limit == -1:
            return {
                "allowed": True,
                "current_usage": 0,
                "remaining": -1,
                "limit": -1,
            }

        now = datetime.utcnow()
        quota_key = self._get_quota_key(tenant_id, quota_type, now.year, now.month)
        reset_ts = self._get_month_end_timestamp()

        # 执行 Lua 脚本进行原子检查和消费
        result = await cache.client.eval(
            CHECK_AND_CONSUME_SCRIPT,
            1,
            quota_key,  # KEYS[1]
            quota_limit,  # ARGV[1]
            amount,  # ARGV[2]
            reset_ts,  # ARGV[3]
        )

        allowed, current_usage, remaining_or_limit = result

        if not allowed:
            # 配额已用完
            raise QuotaExceededException(
                quota_type.value,
                f"{quota_type.value} 配额已用完 (配额: {quota_limit}, 已用: {current_usage})",
            )

        return {
            "allowed": True,
            "current_usage": current_usage,
            "remaining": remaining_or_limit,
            "limit": quota_limit,
        }

    async def get_usage(self, tenant_id: str, quota_type: QuotaType) -> dict[str, Any]:
        """
        获取配额使用情况

        Args:
            tenant_id: 租户 ID
            quota_type: 配额类型

        Returns:
            dict: {
                "current_usage": int,
                "remaining": int,
                "limit": int,
                "percentage": float,
            }
        """
        cache = await get_cache()
        quota_limit = await self._get_quota_limit(tenant_id, quota_type)

        now = datetime.utcnow()
        quota_key = self._get_quota_key(tenant_id, quota_type, now.year, now.month)

        # 执行 Lua 脚本获取使用情况
        result = await cache.client.eval(
            GET_USAGE_SCRIPT,
            1,
            quota_key,  # KEYS[1]
            quota_limit,  # ARGV[1]
        )

        current_usage, remaining = result

        percentage = (
            (current_usage / quota_limit * 100) if quota_limit > 0 else 0
        )

        return {
            "current_usage": current_usage,
            "remaining": remaining,
            "limit": quota_limit,
            "percentage": round(percentage, 2),
        }

    async def get_all_usage(self, tenant_id: str) -> dict[str, dict[str, Any]]:
        """
        获取所有配额的使用情况

        Returns:
            dict: {
                "conversation": {...},
                "concurrent": {...},
                "storage": {...},
                "api": {...},
            }
        """
        usage = {}
        for quota_type in QuotaType:
            usage[quota_type.value] = await self.get_usage(tenant_id, quota_type)
        return usage

    async def record_usage_to_db(
        self,
        tenant_id: str,
        conversation_count: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        storage_used: float = 0.0,
        api_calls: int = 0,
    ) -> UsageRecord:
        """
        将用量记录到数据库（异步批量写入）

        用于月度账单和统计分析
        """
        today = datetime.utcnow().date()

        # 查询今日是否已有记录
        stmt = select(UsageRecord).where(
            and_(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.record_date == today,
            )
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            # 更新现有记录
            record.conversation_count += conversation_count
            record.input_tokens += input_tokens
            record.output_tokens += output_tokens
            record.storage_used = max(record.storage_used, storage_used)
            record.api_calls += api_calls
        else:
            # 创建新记录
            record = UsageRecord(
                tenant_id=tenant_id,
                record_date=today,
                conversation_count=conversation_count,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                storage_used=storage_used,
                api_calls=api_calls,
                overage_fee=0.0,
            )
            self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)

        return record

    async def check_conversation_quota(self, tenant_id: str) -> dict[str, Any]:
        """检查对话次数配额"""
        return await self.check_and_consume(tenant_id, QuotaType.CONVERSATION)

    async def check_api_quota(self, tenant_id: str) -> dict[str, Any]:
        """检查 API 调用配额"""
        return await self.check_and_consume(tenant_id, QuotaType.API)

    async def check_concurrent_quota(self, tenant_id: str, current_count: int) -> bool:
        """检查并发会话配额"""
        quota_limit = await self._get_quota_limit(tenant_id, QuotaType.CONCURRENT)

        if quota_limit == -1:
            return True

        if current_count >= quota_limit:
            raise QuotaExceededException(
                "concurrent",
                f"并发会话数已达上限 ({quota_limit})，请等待或升级套餐",
            )

        return True

    async def check_storage_quota(self, tenant_id: str, additional_gb: float) -> bool:
        """检查存储空间配额"""
        quota_limit = await self._get_quota_limit(tenant_id, QuotaType.STORAGE)

        if quota_limit == -1:
            return True

        # 获取当前使用量（从数据库）
        usage = await self._get_db_storage_usage(tenant_id)

        if usage + additional_gb > quota_limit:
            raise QuotaExceededException(
                "storage",
                f"存储空间不足，当前已用 {usage:.2f}GB，配额 {quota_limit}GB",
            )

        return True

    async def _get_db_storage_usage(self, tenant_id: str) -> float:
        """从数据库获取存储使用量"""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt = select(UsageRecord).where(
            and_(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.record_date >= month_start,
            )
        )
        result = await self.db.execute(stmt)
        records = result.scalars().all()

        # 取最大存储使用量
        return max((r.storage_used for r in records), default=0.0)

    async def reset_monthly_quota(self, tenant_id: str, year: int, month: int):
        """
        重置月度配额（管理员操作或定时任务）

        注意：Redis 中的配额会自动过期，此方法主要用于强制重置
        """
        cache = await get_cache()

        for quota_type in QuotaType:
            quota_key = self._get_quota_key(tenant_id, quota_type, year, month)
            await cache.delete(quota_key)
