"""
配额管理服务
"""
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import QuotaExceededException
from models import Subscription, UsageRecord
from services.subscription_service import SubscriptionService


class QuotaService:
    """配额管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_service = SubscriptionService(db)

    async def check_conversation_quota(self, tenant_id: str) -> bool:
        """
        检查对话次数配额
        
        Raises:
            QuotaExceededException: 配额已用完且未开启超额付费
        """
        subscription = await self.subscription_service.get_subscription(tenant_id)
        usage = await self.get_current_month_usage(tenant_id)

        if usage.conversation_count >= subscription.conversation_quota:
            # 检查是否开启超额付费（暂时默认开启）
            # TODO: 从配置中获取是否允许超额
            allow_overage = True
            if not allow_overage:
                raise QuotaExceededException(
                    "对话次数",
                    f"对话次数配额({subscription.conversation_quota})已用完，请升级套餐",
                )

        return True

    async def check_concurrent_quota(self, tenant_id: str, current_count: int) -> bool:
        """
        检查并发会话数配额
        
        Args:
            tenant_id: 租户ID
            current_count: 当前并发会话数
        """
        subscription = await self.subscription_service.get_subscription(tenant_id)

        if current_count >= subscription.concurrent_quota:
            raise QuotaExceededException(
                "并发会话",
                f"并发会话数已达上限({subscription.concurrent_quota})，请等待或升级套餐",
            )

        return True

    async def check_storage_quota(self, tenant_id: str, additional_size: float) -> bool:
        """
        检查存储空间配额
        
        Args:
            tenant_id: 租户ID
            additional_size: 需要新增的存储大小(GB)
        """
        subscription = await self.subscription_service.get_subscription(tenant_id)
        usage = await self.get_current_month_usage(tenant_id)

        if usage.storage_used + additional_size > subscription.storage_quota:
            raise QuotaExceededException(
                "存储空间",
                f"存储空间不足，当前已用 {usage.storage_used}GB，配额 {subscription.storage_quota}GB",
            )

        return True

    async def check_api_quota(self, tenant_id: str) -> bool:
        """检查API调用配额"""
        subscription = await self.subscription_service.get_subscription(tenant_id)
        usage = await self.get_current_month_usage(tenant_id)

        if usage.api_calls >= subscription.api_quota:
            raise QuotaExceededException(
                "API调用",
                f"API调用次数配额({subscription.api_quota})已用完",
            )

        return True

    async def get_current_month_usage(self, tenant_id: str) -> UsageRecord:
        """
        获取当月用量记录
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
        """
        获取配额使用情况
        """
        subscription = await self.subscription_service.get_subscription(tenant_id)
        usage = await self.get_current_month_usage(tenant_id)

        return {
            "conversation": {
                "quota": subscription.conversation_quota,
                "used": usage.conversation_count,
                "percentage": (
                    usage.conversation_count / subscription.conversation_quota * 100
                    if subscription.conversation_quota > 0
                    else 0
                ),
            },
            "storage": {
                "quota": subscription.storage_quota,
                "used": usage.storage_used,
                "percentage": (
                    usage.storage_used / subscription.storage_quota * 100
                    if subscription.storage_quota > 0
                    else 0
                ),
            },
            "api": {
                "quota": subscription.api_quota,
                "used": usage.api_calls,
                "percentage": (
                    usage.api_calls / subscription.api_quota * 100
                    if subscription.api_quota > 0
                    else 0
                ),
            },
        }

    async def adjust_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int,
        reason: str | None = None,
    ) -> Subscription:
        """
        调整配额（管理员操作）
        
        Args:
            tenant_id: 租户ID
            quota_type: 配额类型(conversation/storage/api)
            amount: 调整数量（正数为增加，负数为减少）
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
        查询超配额租户（告警）
        
        Args:
            threshold: 阈值（0.9表示90%）
        """
        # 查询所有活跃租户
        stmt = select(Subscription).where(Subscription.status == "active")
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()

        over_quota_list = []

        for subscription in subscriptions:
            usage = await self.get_current_month_usage(subscription.tenant_id)

            # 检查各项配额使用率
            quota_status = {
                "conversation": (
                    usage.conversation_count / subscription.conversation_quota
                    if subscription.conversation_quota > 0
                    else 0
                ),
                "storage": (
                    usage.storage_used / subscription.storage_quota
                    if subscription.storage_quota > 0
                    else 0
                ),
                "api": (
                    usage.api_calls / subscription.api_quota
                    if subscription.api_quota > 0
                    else 0
                ),
            }

            # 如果任一项超过阈值
            if any(usage_rate > threshold for usage_rate in quota_status.values()):
                over_quota_list.append(
                    {
                        "tenant_id": subscription.tenant_id,
                        "quota_status": quota_status,
                        "usage": {
                            "conversation": usage.conversation_count,
                            "storage": usage.storage_used,
                            "api": usage.api_calls,
                        },
                    }
                )

        return over_quota_list
