"""
配额管理服务(优化版 - 支持Redis原子操作)
"""
import json
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from core.exceptions import QuotaExceededException
from models import Subscription, UsageRecord, QuotaAdjustmentLog
from services.subscription_service import SubscriptionService


class QuotaType(Enum):
    """配额类型"""
    CONVERSATION = "conversation"      # 对话次数(月)
    API_CALL = "api_call"              # API调用次数(月)
    STORAGE = "storage"                # 存储空间(MB)
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


@dataclass
class QuotaConfig:
    """套餐配额配置"""
    conversation_quota: int      # 月对话次数
    api_quota: int               # 月API调用次数
    storage_quota: int           # 存储空间(MB)
    concurrent_quota: int        # 并发会话数
    knowledge_quota: int         # 知识库条目数
    over_limit_strategy: OverLimitStrategy


# 套餐配额定义
PLAN_QUOTAS = {
    "free": QuotaConfig(
        conversation_quota=100,
        api_quota=1000,
        storage_quota=100,      # 100MB
        concurrent_quota=1,
        knowledge_quota=100,
        over_limit_strategy=OverLimitStrategy.UPGRADE_PROMPT
    ),
    "basic": QuotaConfig(
        conversation_quota=1000,
        api_quota=10000,
        storage_quota=1024,     # 1GB
        concurrent_quota=5,
        knowledge_quota=1000,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
    "professional": QuotaConfig(
        conversation_quota=10000,
        api_quota=100000,
        storage_quota=10240,    # 10GB
        concurrent_quota=20,
        knowledge_quota=10000,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
    "enterprise": QuotaConfig(
        conversation_quota=-1,   # 无限制
        api_quota=-1,
        storage_quota=102400,   # 100GB
        concurrent_quota=100,
        knowledge_quota=-1,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
}


class QuotaService:
    """配额管理服务(优化版)"""

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
        self.subscription_service = SubscriptionService(db)

    async def check_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """
        检查配额是否足够(不消耗)

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 请求消耗的数量

        Returns:
            QuotaCheckResult: 检查结果
        """
        # 获取租户订阅和配额配置
        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan_type, PLAN_QUOTAS["free"])

        # 获取配额限制
        limit = self._get_quota_limit(quota_config, quota_type)

        # 无限制(-1)直接通过
        if limit == -1:
            return QuotaCheckResult(
                allowed=True,
                quota_type=quota_type,
                used=0,
                limit=-1,
                remaining=-1
            )

        # 获取当前用量
        used = await self._get_current_usage_redis(tenant_id, quota_type)
        remaining = max(0, limit - used)

        # 检查是否超限
        if used + amount > limit:
            return QuotaCheckResult(
                allowed=False,
                quota_type=quota_type,
                used=used,
                limit=limit,
                remaining=remaining,
                strategy=quota_config.over_limit_strategy,
                message=self._get_over_limit_message(quota_type, quota_config)
            )

        return QuotaCheckResult(
            allowed=True,
            quota_type=quota_type,
            used=used,
            limit=limit,
            remaining=remaining - amount
        )

    async def consume_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> bool:
        """
        消耗配额(仅记录,不检查)

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 消耗数量

        Returns:
            bool: 是否成功
        """
        if not self.redis:
            return True

        # 使用Redis原子操作
        key = self._get_usage_key(tenant_id, quota_type)
        new_value = await self.redis.incrby(key, amount)

        # 设置过期时间(月末过期)
        ttl = await self.redis.ttl(key)
        if ttl == -1:  # 没有设置过期时间
            expire_at = self._get_month_end_timestamp()
            await self.redis.expireat(key, expire_at)

        return True

    async def check_and_consume(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """
        检查并消耗配额(原子操作)

        使用Redis Lua脚本确保原子性
        """
        if not self.redis:
            # 如果没有Redis,降级到非原子操作
            result = await self.check_quota(tenant_id, quota_type, amount)
            if result.allowed:
                await self.consume_quota(tenant_id, quota_type, amount)
            return result

        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan_type, PLAN_QUOTAS["free"])
        limit = self._get_quota_limit(quota_config, quota_type)

        # Lua脚本实现原子检查和消耗
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local amount = tonumber(ARGV[2])
        local expire_at = tonumber(ARGV[3])

        -- 无限制直接通过
        if limit == -1 then
            return {1, 0, -1}
        end

        local current = tonumber(redis.call('GET', key) or 0)

        -- 检查是否超限
        if current + amount > limit then
            return {0, current, limit}
        end

        -- 消耗配额
        local new_value = redis.call('INCRBY', key, amount)

        -- 设置过期时间
        local ttl = redis.call('TTL', key)
        if ttl == -1 then
            redis.call('EXPIREAT', key, expire_at)
        end

        return {1, new_value, limit}
        """

        key = self._get_usage_key(tenant_id, quota_type)
        expire_at = self._get_month_end_timestamp()

        result = await self.redis.eval(
            lua_script,
            1,
            key,
            limit,
            amount,
            expire_at
        )

        allowed, used, actual_limit = int(result[0]), int(result[1]), int(result[2])

        if not allowed:
            return QuotaCheckResult(
                allowed=False,
                quota_type=quota_type,
                used=used,
                limit=actual_limit,
                remaining=0,
                strategy=quota_config.over_limit_strategy,
                message=self._get_over_limit_message(quota_type, quota_config)
            )

        return QuotaCheckResult(
            allowed=True,
            quota_type=quota_type,
            used=used,
            limit=actual_limit,
            remaining=max(0, actual_limit - used)
        )

    async def get_quota_status(self, tenant_id: str) -> dict:
        """
        获取租户所有配额状态

        Returns:
            {
                "conversation": {"used": 50, "limit": 100, "percentage": 50},
                "api_call": {...},
                ...
            }
        """
        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan_type, PLAN_QUOTAS["free"])

        status = {}
        for quota_type in QuotaType:
            limit = self._get_quota_limit(quota_config, quota_type)
            used = await self._get_current_usage_redis(tenant_id, quota_type)

            if limit == -1:
                percentage = 0
            else:
                percentage = round(used / limit * 100, 2) if limit > 0 else 0

            status[quota_type.value] = {
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used) if limit != -1 else -1,
                "percentage": percentage
            }

        return status

    async def reset_monthly_quota(self, tenant_id: str):
        """重置月度配额(每月1日调用)"""
        if not self.redis:
            return

        for quota_type in [QuotaType.CONVERSATION, QuotaType.API_CALL]:
            key = self._get_usage_key(tenant_id, quota_type)
            await self.redis.delete(key)

    async def adjust_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        adjustment: int,
        reason: str,
        operator_id: str = None,
        operator_type: str = "admin",
        ip_address: str = None,
        user_agent: str = None,
        metadata: dict = None
    ):
        """
        调整配额(管理员操作)

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            adjustment: 正数增加额度(减少已用量),负数减少额度(增加已用量)
            reason: 调整原因
            operator_id: 操作人ID
            operator_type: 操作人类型(admin/system/api)
            ip_address: 操作IP地址
            user_agent: 用户代理
            metadata: 额外信息
        """
        # 获取调整前的值
        before_value = await self._get_current_usage_redis(tenant_id, quota_type)

        # 更新Redis
        if self.redis:
            key = self._get_usage_key(tenant_id, quota_type)
            if adjustment < 0:
                # 负数调整=减少额度=增加已用量
                await self.redis.incrby(key, abs(adjustment))
            else:
                # 正数调整=增加额度=减少已用量
                new_value = max(0, before_value - adjustment)
                await self.redis.set(key, new_value)

        # 获取调整后的值
        after_value = await self._get_current_usage_redis(tenant_id, quota_type)

        # 记录到数据库审计日志
        log = QuotaAdjustmentLog(
            tenant_id=tenant_id,
            quota_type=quota_type.value,
            adjustment=adjustment,
            before_value=before_value,
            after_value=after_value,
            operator_id=operator_id,
            operator_type=operator_type,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
        self.db.add(log)
        await self.db.commit()

        return log

    async def record_overage(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int
    ):
        """
        记录超额使用(用于按量付费模式)

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 超额数量
        """
        if not self.redis:
            return

        # 记录超额使用
        overage_key = f"overage:{tenant_id}:{quota_type.value}:{datetime.now().strftime('%Y%m')}"
        await self.redis.incrby(overage_key, amount)

        # 设置过期时间(3个月)
        await self.redis.expire(overage_key, 86400 * 90)

    # ===== 私有方法 =====

    def _get_usage_key(self, tenant_id: str, quota_type: QuotaType) -> str:
        """获取Redis用量key"""
        month = datetime.now().strftime("%Y%m")
        return f"quota:{tenant_id}:{quota_type.value}:{month}"

    def _get_quota_limit(self, config: QuotaConfig, quota_type: QuotaType) -> int:
        """获取配额限制"""
        mapping = {
            QuotaType.CONVERSATION: config.conversation_quota,
            QuotaType.API_CALL: config.api_quota,
            QuotaType.STORAGE: config.storage_quota,
            QuotaType.CONCURRENT: config.concurrent_quota,
            QuotaType.KNOWLEDGE_ITEMS: config.knowledge_quota,
        }
        return mapping.get(quota_type, 0)

    async def _get_current_usage_redis(self, tenant_id: str, quota_type: QuotaType) -> int:
        """从Redis获取当前用量"""
        if not self.redis:
            # 降级到数据库查询
            return await self._get_current_usage_db(tenant_id, quota_type)

        key = self._get_usage_key(tenant_id, quota_type)
        value = await self.redis.get(key)
        return int(value) if value else 0

    async def _get_current_usage_db(self, tenant_id: str, quota_type: QuotaType) -> int:
        """从数据库获取当前用量(Redis降级方案)"""
        usage = await self.get_current_month_usage(tenant_id)

        mapping = {
            QuotaType.CONVERSATION: usage.conversation_count,
            QuotaType.API_CALL: usage.api_calls,
            QuotaType.STORAGE: int(usage.storage_used),
            QuotaType.KNOWLEDGE_ITEMS: 0,  # TODO: 需要从knowledge表统计
        }
        return mapping.get(quota_type, 0)

    async def _get_subscription(self, tenant_id: str) -> Subscription:
        """获取订阅信息(带缓存)"""
        if not self.redis:
            return await self.subscription_service.get_subscription(tenant_id)

        cache_key = f"subscription:{tenant_id}"
        cached = await self.redis.get(cache_key)

        if cached:
            data = json.loads(cached)
            # 这里简化处理,实际应该返回完整的Subscription对象
            # 为了简化,直接查询数据库
            pass

        subscription = await self.subscription_service.get_subscription(tenant_id)

        # 缓存5分钟
        await self.redis.setex(
            cache_key,
            300,
            json.dumps({
                "plan_type": subscription.plan_type,
                "status": subscription.status
            })
        )

        return subscription

    def _get_month_end_timestamp(self) -> int:
        """获取本月最后一天的Unix时间戳"""
        today = date.today()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        month_end = datetime.combine(next_month, datetime.min.time())
        return int(month_end.timestamp())

    def _get_over_limit_message(
        self,
        quota_type: QuotaType,
        config: QuotaConfig
    ) -> str:
        """获取超限提示消息"""
        messages = {
            QuotaType.CONVERSATION: "本月对话次数已用完",
            QuotaType.API_CALL: "本月API调用次数已用完",
            QuotaType.STORAGE: "存储空间已用完",
            QuotaType.CONCURRENT: "并发会话数已达上限",
            QuotaType.KNOWLEDGE_ITEMS: "知识库条目数已达上限",
        }

        base_msg = messages.get(quota_type, "配额已用完")

        if config.over_limit_strategy == OverLimitStrategy.UPGRADE_PROMPT:
            return f"{base_msg},请升级套餐获取更多额度"
        elif config.over_limit_strategy == OverLimitStrategy.PAY_AS_YOU_GO:
            return f"{base_msg},超出部分将按量计费"
        else:
            return base_msg

    # ===== 兼容旧版本的方法 =====

    async def check_conversation_quota(self, tenant_id: str) -> bool:
        """
        检查对话次数配额(兼容旧版本)

        Raises:
            QuotaExceededException: 配额已用完且未开启超额付费
        """
        result = await self.check_quota(tenant_id, QuotaType.CONVERSATION, 1)

        if not result.allowed:
            if result.strategy == OverLimitStrategy.UPGRADE_PROMPT:
                raise QuotaExceededException(
                    "对话次数",
                    result.message
                )
            elif result.strategy == OverLimitStrategy.PAY_AS_YOU_GO:
                # 按量付费模式,记录超额并允许继续
                await self.record_overage(tenant_id, QuotaType.CONVERSATION, 1)
                return True

        return True

    async def check_concurrent_quota(self, tenant_id: str, current_count: int) -> bool:
        """检查并发会话数配额(兼容旧版本)"""
        result = await self.check_quota(tenant_id, QuotaType.CONCURRENT, current_count)

        if not result.allowed:
            raise QuotaExceededException(
                "并发会话",
                result.message
            )

        return True

    async def check_storage_quota(self, tenant_id: str, additional_size: float) -> bool:
        """检查存储空间配额(兼容旧版本)"""
        result = await self.check_quota(tenant_id, QuotaType.STORAGE, int(additional_size))

        if not result.allowed:
            raise QuotaExceededException(
                "存储空间",
                result.message
            )

        return True

    async def check_api_quota(self, tenant_id: str) -> bool:
        """检查API调用配额(兼容旧版本)"""
        result = await self.check_quota(tenant_id, QuotaType.API_CALL, 1)

        if not result.allowed:
            raise QuotaExceededException(
                "API调用",
                result.message
            )

        return True

    async def get_current_month_usage(self, tenant_id: str) -> UsageRecord:
        """
        获取当月用量记录(从数据库)
        """
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)

        # 查询当月所有用量记录
        stmt = select(UsageRecord).where(
            and_(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.record_date >= month_start,
            )
        )
        result = await self.db.execute(stmt)
        records = result.scalars().all()

        # 汇总用量
        total_usage = UsageRecord(
            tenant_id=tenant_id,
            record_date=month_start,
            conversation_count=sum(r.conversation_count for r in records),
            input_tokens=sum(r.input_tokens for r in records),
            output_tokens=sum(r.output_tokens for r in records),
            storage_used=max((r.storage_used for r in records), default=0.0),
            api_calls=sum(r.api_calls for r in records),
            overage_fee=sum(r.overage_fee for r in records),
        )

        return total_usage

    async def get_quota_usage(self, tenant_id: str) -> dict:
        """获取配额使用情况(兼容旧版本)"""
        return await self.get_quota_status(tenant_id)

    async def adjust_subscription_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int,
        reason: str | None = None,
    ) -> Subscription:
        """
        调整订阅配额限制(管理员操作)

        注意: 此方法直接修改订阅的配额上限,而非已用量

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型 (conversation/storage/api)
            amount: 调整量
            reason: 调整原因
        """
        subscription = await self.subscription_service.get_subscription(tenant_id)

        if quota_type == "conversation":
            subscription.conversation_quota += amount
        elif quota_type == "storage":
            subscription.storage_quota += amount
        elif quota_type == "api":
            subscription.api_quota += amount
        else:
            raise ValueError(f"不支持的配额类型: {quota_type}")

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def get_over_quota_tenants(self, threshold: float = 0.9) -> list[dict]:
        """
        查询超配额租户(告警)
        """
        # 查询所有活跃租户
        stmt = select(Subscription).where(Subscription.status == "active")
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()

        over_quota_list = []

        for subscription in subscriptions:
            status = await self.get_quota_status(subscription.tenant_id)

            # 检查各项配额使用率
            quota_rates = {
                key: (data["used"] / data["limit"] if data["limit"] > 0 and data["limit"] != -1 else 0)
                for key, data in status.items()
            }

            # 如果任一项超过阈值
            if any(rate > threshold for rate in quota_rates.values()):
                over_quota_list.append({
                    "tenant_id": subscription.tenant_id,
                    "quota_status": quota_rates,
                    "usage": status,
                })

        return over_quota_list