"""
用量统计服务
"""
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Subscription, UsageRecord
from services.subscription_service import SubscriptionService


class UsageService:
    """用量统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_service = SubscriptionService(db)

    async def get_or_create_usage(
        self, tenant_id: str, record_date: datetime
    ) -> UsageRecord:
        """获取或创建用量记录"""
        stmt = select(UsageRecord).where(
            and_(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.record_date == record_date,
            )
        )
        result = await self.db.execute(stmt)
        usage = result.scalar_one_or_none()

        if not usage:
            usage = UsageRecord(tenant_id=tenant_id, record_date=record_date)
            self.db.add(usage)
            await self.db.commit()
            await self.db.refresh(usage)

        return usage

    async def record_conversation(
        self,
        tenant_id: str,
        conversation_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> UsageRecord:
        """
        记录对话用量
        """
        today = datetime.utcnow().date()
        usage = await self.get_or_create_usage(tenant_id, today)

        # 更新用量
        usage.conversation_count += 1
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens

        # 计算超额费用
        subscription = await self.subscription_service.get_subscription(tenant_id)
        if usage.conversation_count > subscription.conversation_quota:
            overage = usage.conversation_count - subscription.conversation_quota
            usage.overage_fee += overage * 0.1  # 每次对话超额费用 0.1 元

        await self.db.commit()
        await self.db.refresh(usage)

        return usage

    async def record_api_call(self, tenant_id: str) -> UsageRecord:
        """记录API调用"""
        today = datetime.utcnow().date()
        usage = await self.get_or_create_usage(tenant_id, today)

        usage.api_calls += 1

        # 计算超额费用
        subscription = await self.subscription_service.get_subscription(tenant_id)
        if usage.api_calls > subscription.api_quota:
            overage = usage.api_calls - subscription.api_quota
            usage.overage_fee += overage * 0.01  # 每次API调用超额费用 0.01 元

        await self.db.commit()
        await self.db.refresh(usage)

        return usage

    async def update_storage_usage(self, tenant_id: str, storage_used: float) -> UsageRecord:
        """更新存储使用量"""
        today = datetime.utcnow().date()
        usage = await self.get_or_create_usage(tenant_id, today)

        usage.storage_used = storage_used

        # 计算超额费用
        subscription = await self.subscription_service.get_subscription(tenant_id)
        if usage.storage_used > subscription.storage_quota:
            overage = usage.storage_used - subscription.storage_quota
            usage.overage_fee += overage * 0.5  # 每GB超额费用 0.5 元/月

        await self.db.commit()
        await self.db.refresh(usage)

        return usage

    async def get_monthly_usage(
        self, tenant_id: str, year: int, month: int
    ) -> list[UsageRecord]:
        """获取指定月份的用量记录"""
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        stmt = (
            select(UsageRecord)
            .where(
                and_(
                    UsageRecord.tenant_id == tenant_id,
                    UsageRecord.record_date >= start_date,
                    UsageRecord.record_date < end_date,
                )
            )
            .order_by(UsageRecord.record_date)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_usage_summary(self, tenant_id: str, year: int, month: int) -> dict:
        """获取月度用量汇总"""
        records = await self.get_monthly_usage(tenant_id, year, month)

        return {
            "tenant_id": tenant_id,
            "period": f"{year}-{month:02d}",
            "total_conversations": sum(r.conversation_count for r in records),
            "total_input_tokens": sum(r.input_tokens for r in records),
            "total_output_tokens": sum(r.output_tokens for r in records),
            "max_storage_used": max((r.storage_used for r in records), default=0.0),
            "total_api_calls": sum(r.api_calls for r in records),
            "total_overage_fee": sum(r.overage_fee for r in records),
        }
