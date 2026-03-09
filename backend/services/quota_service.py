"""
配额服务 - 配额检查、扣减、重置
"""
import logging
from datetime import datetime

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.permissions import get_quota_config
from models.quota import TenantQuota
from models.tenant import Subscription

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """配额超限异常"""

    def __init__(self, quota_type: str, quota: int, used: int):
        self.quota_type = quota_type
        self.quota = quota
        self.used = used
        super().__init__(
            f"{quota_type} 配额已用完（{used}/{quota}），本月无法继续使用"
        )


class QuotaService:
    """配额服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _current_period() -> str:
        """获取当前账期 (YYYY-MM)"""
        return datetime.utcnow().strftime("%Y-%m")

    async def _get_plan_type(self, tenant_id: str) -> str:
        """获取租户当前套餐类型"""
        stmt = select(Subscription.plan_type).where(
            and_(
                Subscription.tenant_id == tenant_id,
                Subscription.status == "active",
            )
        ).order_by(Subscription.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        plan_type = result.scalar_one_or_none()
        return plan_type or "trial"

    async def get_or_create_quota(self, tenant_id: str) -> TenantQuota:
        """获取或创建当月配额记录"""
        period = self._current_period()
        stmt = select(TenantQuota).where(
            and_(
                TenantQuota.tenant_id == tenant_id,
                TenantQuota.billing_period == period,
            )
        )
        result = await self.db.execute(stmt)
        quota = result.scalar_one_or_none()

        if quota:
            return quota

        # 创建新配额记录
        plan_type = await self._get_plan_type(tenant_id)
        config = get_quota_config(plan_type)

        quota = TenantQuota(
            tenant_id=tenant_id,
            billing_period=period,
            reply_quota=config["reply_quota"],
            reply_used=0,
            image_gen_quota=config["image_gen_quota"],
            image_gen_used=0,
            video_gen_quota=config["video_gen_quota"],
            video_gen_used=0,
        )
        self.db.add(quota)
        await self.db.flush()
        return quota

    async def check_reply_quota(self, tenant_id: str) -> TenantQuota:
        """检查AI回复配额，不足则抛出异常"""
        quota = await self.get_or_create_quota(tenant_id)
        if quota.reply_used >= quota.reply_quota:
            raise QuotaExceededError("AI回复", quota.reply_quota, quota.reply_used)
        return quota

    async def check_image_quota(self, tenant_id: str) -> TenantQuota:
        """检查图片生成配额"""
        quota = await self.get_or_create_quota(tenant_id)
        if quota.image_gen_used >= quota.image_gen_quota:
            raise QuotaExceededError("图片生成", quota.image_gen_quota, quota.image_gen_used)
        return quota

    async def check_video_quota(self, tenant_id: str) -> TenantQuota:
        """检查视频生成配额"""
        quota = await self.get_or_create_quota(tenant_id)
        if quota.video_gen_used >= quota.video_gen_quota:
            raise QuotaExceededError("视频生成", quota.video_gen_quota, quota.video_gen_used)
        return quota

    async def increment_reply(self, tenant_id: str) -> None:
        """扣减一次AI回复配额"""
        period = self._current_period()
        stmt = (
            update(TenantQuota)
            .where(
                and_(
                    TenantQuota.tenant_id == tenant_id,
                    TenantQuota.billing_period == period,
                )
            )
            .values(reply_used=TenantQuota.reply_used + 1)
        )
        await self.db.execute(stmt)

    async def increment_image(self, tenant_id: str) -> None:
        """扣减一次图片生成配额"""
        period = self._current_period()
        stmt = (
            update(TenantQuota)
            .where(
                and_(
                    TenantQuota.tenant_id == tenant_id,
                    TenantQuota.billing_period == period,
                )
            )
            .values(image_gen_used=TenantQuota.image_gen_used + 1)
        )
        await self.db.execute(stmt)

    async def increment_video(self, tenant_id: str) -> None:
        """扣减一次视频生成配额"""
        period = self._current_period()
        stmt = (
            update(TenantQuota)
            .where(
                and_(
                    TenantQuota.tenant_id == tenant_id,
                    TenantQuota.billing_period == period,
                )
            )
            .values(video_gen_used=TenantQuota.video_gen_used + 1)
        )
        await self.db.execute(stmt)

    async def reset_all_quotas(self, period: str) -> int:
        """
        为所有活跃租户创建新月度配额记录。
        由 Celery Beat 每月1号调用。
        返回创建的记录数。
        """
        # 查询所有活跃订阅的租户
        stmt = select(Subscription.tenant_id, Subscription.plan_type).where(
            Subscription.status == "active"
        )
        result = await self.db.execute(stmt)
        active_subs = result.all()

        count = 0
        for tenant_id, plan_type in active_subs:
            # 检查是否已存在该月记录
            existing = await self.db.execute(
                select(TenantQuota.id).where(
                    and_(
                        TenantQuota.tenant_id == tenant_id,
                        TenantQuota.billing_period == period,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            config = get_quota_config(plan_type)
            quota = TenantQuota(
                tenant_id=tenant_id,
                billing_period=period,
                reply_quota=config["reply_quota"],
                reply_used=0,
                image_gen_quota=config["image_gen_quota"],
                image_gen_used=0,
                video_gen_quota=config["video_gen_quota"],
                video_gen_used=0,
            )
            self.db.add(quota)
            count += 1

        await self.db.flush()
        return count
