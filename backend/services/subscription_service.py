"""
订阅管理服务
"""
import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ResourceNotFoundException
from core.permissions import PLAN_CONFIGS
from models import Subscription


class SubscriptionService:
    """订阅管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_subscription(self, tenant_id: str) -> Subscription:
        """获取租户订阅"""
        stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .order_by(Subscription.created_at.desc())
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ResourceNotFoundException("订阅", tenant_id)

        return subscription

    async def assign_plan(
        self,
        tenant_id: str,
        plan_type: str,
        duration_months: int = 1,
        auto_renew: bool = False,
    ) -> Subscription:
        """
        分配套餐
        """
        # 获取或创建订阅
        try:
            subscription = await self.get_subscription(tenant_id)
        except ResourceNotFoundException:
            subscription = Subscription(tenant_id=tenant_id)
            self.db.add(subscription)

        # 更新套餐信息
        plan_config = PLAN_CONFIGS.get(plan_type, PLAN_CONFIGS["free"])

        subscription.plan_type = plan_type
        subscription.status = "active"
        subscription.start_date = datetime.utcnow()
        subscription.expire_at = datetime.utcnow() + timedelta(days=duration_months * 30)
        subscription.auto_renew = auto_renew
        subscription.is_trial = False

        # 根据套餐设置配额
        subscription.enabled_features = json.dumps([f.value for f in plan_config["features"]])  # 转换为JSON字符串
        subscription.conversation_quota = plan_config["conversation_quota"]
        subscription.concurrent_quota = plan_config["concurrent_quota"]
        subscription.storage_quota = plan_config["storage_quota"]
        subscription.api_quota = plan_config["api_quota"]

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def change_plan(
        self,
        tenant_id: str,
        new_plan: str,
        effective_date: datetime | None = None,
    ) -> Subscription:
        """
        变更套餐（升级/降级）
        """
        subscription = await self.get_subscription(tenant_id)

        # 立即生效
        if not effective_date or effective_date <= datetime.utcnow():
            plan_config = PLAN_CONFIGS.get(new_plan, PLAN_CONFIGS["free"])

            subscription.plan_type = new_plan
            subscription.enabled_features = json.dumps([f.value for f in plan_config["features"]])  # 转换为JSON字符串
            subscription.conversation_quota = plan_config["conversation_quota"]
            subscription.concurrent_quota = plan_config["concurrent_quota"]
            subscription.storage_quota = plan_config["storage_quota"]
            subscription.api_quota = plan_config["api_quota"]
        else:
            # 延期生效
            subscription.pending_plan = new_plan
            subscription.plan_change_date = effective_date

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def extend_service(
        self,
        tenant_id: str,
        days: int,
    ) -> Subscription:
        """延长服务期限"""
        subscription = await self.get_subscription(tenant_id)
        subscription.expire_at += timedelta(days=days)

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def create_trial(
        self,
        tenant_id: str,
        trial_days: int = 30,
    ) -> Subscription:
        """创建试用账号"""
        subscription = await self.assign_plan(
            tenant_id=tenant_id,
            plan_type="basic",
            duration_months=0,
        )
        subscription.is_trial = True
        subscription.expire_at = datetime.utcnow() + timedelta(days=trial_days)

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def check_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """检查功能模块是否已开通"""
        subscription = await self.get_subscription(tenant_id)
        features = json.loads(subscription.enabled_features) if isinstance(subscription.enabled_features, str) else subscription.enabled_features
        return feature in features

    async def grant_feature(
        self,
        tenant_id: str,
        feature: str,
        config: dict | None = None,
    ) -> Subscription:
        """授予功能模块"""
        subscription = await self.get_subscription(tenant_id)

        # 解析JSON字符串为列表
        features = json.loads(subscription.enabled_features) if isinstance(subscription.enabled_features, str) else subscription.enabled_features

        if feature not in features:
            features.append(feature)
            # 保存为JSON字符串
            subscription.enabled_features = json.dumps(features)

        # 更新功能配置
        if config:
            if not subscription.feature_config:
                subscription.feature_config = {}
            subscription.feature_config[feature] = config

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def revoke_feature(self, tenant_id: str, feature: str) -> Subscription:
        """撤销功能模块"""
        subscription = await self.get_subscription(tenant_id)

        # 解析JSON字符串为列表
        features = json.loads(subscription.enabled_features) if isinstance(subscription.enabled_features, str) else subscription.enabled_features

        if feature in features:
            features.remove(feature)
            # 保存为JSON字符串
            subscription.enabled_features = json.dumps(features)

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def batch_extend_service(
        self,
        tenant_ids: list[str],
        days: int,
    ) -> dict:
        """批量延长服务期限"""
        results = {"success": [], "failed": []}

        for tenant_id in tenant_ids:
            try:
                await self.extend_service(tenant_id=tenant_id, days=days)
                results["success"].append(tenant_id)
            except Exception as e:
                results["failed"].append({"tenant_id": tenant_id, "error": str(e)})

        await self.db.commit()

        return results
