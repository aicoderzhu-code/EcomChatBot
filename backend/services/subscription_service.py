"""
订阅管理服务
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from core.exceptions import ResourceNotFoundException
from core.permissions import PLAN_CONFIGS, SUBSCRIPTION_PLANS
from models import Subscription
from models.tenant import Tenant, Bill
from models.payment import PaymentOrder, OrderStatus

logger = logging.getLogger(__name__)


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
        days: int | None = None,
        auto_renew: bool = False,
    ) -> Subscription:
        """
        分配套餐

        Args:
            tenant_id: 租户ID
            plan_type: 套餐类型
            duration_months: 订阅时长（月），当 days 未指定且 plan_type 不在 SUBSCRIPTION_PLANS 时使用
            days: 订阅天数（优先于 duration_months；若 plan_type 在 SUBSCRIPTION_PLANS 中则自动读取）
            auto_renew: 是否自动续费
        """
        # 获取或创建订阅
        try:
            subscription = await self.get_subscription(tenant_id)
        except ResourceNotFoundException:
            subscription = Subscription(tenant_id=tenant_id)
            self.db.add(subscription)

        # 确定订阅天数
        if plan_type in SUBSCRIPTION_PLANS:
            effective_days = days if days is not None else SUBSCRIPTION_PLANS[plan_type]["days"]
        elif days is not None:
            effective_days = days
        else:
            effective_days = duration_months * 30

        # 计算到期时间：若当前订阅未过期则叠加，否则从现在开始
        now = datetime.utcnow()
        if subscription.expire_at and subscription.expire_at > now:
            new_expire_at = subscription.expire_at + timedelta(days=effective_days)
        else:
            new_expire_at = now + timedelta(days=effective_days)

        # 更新套餐信息
        plan_config = PLAN_CONFIGS.get(plan_type, PLAN_CONFIGS["free"])

        subscription.plan_type = plan_type
        subscription.status = "active"
        subscription.start_date = now
        subscription.expire_at = new_expire_at
        subscription.auto_renew = auto_renew
        subscription.is_trial = plan_type == "trial"

        # 根据套餐设置配额
        features = plan_config["features"]
        subscription.enabled_features = json.dumps([f.value if hasattr(f, 'value') else f for f in features])
        subscription.conversation_quota = plan_config["conversation_quota"]
        subscription.concurrent_quota = plan_config["concurrent_quota"]
        subscription.storage_quota = plan_config["storage_quota"]
        subscription.api_quota = plan_config["api_quota"]

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def get_subscription_with_grace(self, tenant_id: str) -> dict:
        """返回订阅信息，包含宽限期状态"""
        subscription = await self.get_subscription(tenant_id)
        now = datetime.utcnow()
        grace_period_end = subscription.expire_at + timedelta(days=7) if subscription.expire_at else None

        if not subscription.expire_at:
            status = "active"
            is_in_grace = False
        elif subscription.expire_at > now:
            status = "active"
            is_in_grace = False
        elif grace_period_end and grace_period_end > now:
            status = "grace"
            is_in_grace = True
        else:
            status = "expired"
            is_in_grace = False

        plan_info = SUBSCRIPTION_PLANS.get(subscription.plan_type, {})

        return {
            "subscription_id": subscription.subscription_id,
            "plan_type": subscription.plan_type,
            "plan_name": plan_info.get("name", subscription.plan_type),
            "status": status,
            "expire_at": subscription.expire_at.isoformat() if subscription.expire_at else None,
            "grace_period_end": grace_period_end.isoformat() if grace_period_end else None,
            "is_in_grace": is_in_grace,
            "is_trial": subscription.is_trial,
        }

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
    
    async def batch_upgrade_plan(
        self,
        tenant_ids: list[str],
        new_plan: str,
    ) -> dict:
        """
        批量升级套餐
        
        Args:
            tenant_ids: 租户ID列表
            new_plan: 新套餐类型
            
        Returns:
            {"success": [...], "failed": [...]}
        """
        results = {"success": [], "failed": []}
        
        for tenant_id in tenant_ids:
            try:
                subscription = await self.get_subscription(tenant_id)
                subscription.plan_type = new_plan
                subscription.updated_at = datetime.utcnow()
                await self.db.commit()
                results["success"].append(tenant_id)
            except Exception as e:
                results["failed"].append({"tenant_id": tenant_id, "error": str(e)})
        
        return results
    
    async def batch_downgrade_plan(
        self,
        tenant_ids: list[str],
        new_plan: str,
    ) -> dict:
        """
        批量降级套餐
        
        Args:
            tenant_ids: 租户ID列表
            new_plan: 新套餐类型
            
        Returns:
            {"success": [...], "failed": [...]}
        """
        results = {"success": [], "failed": []}
        
        for tenant_id in tenant_ids:
            try:
                subscription = await self.get_subscription(tenant_id)
                subscription.plan_type = new_plan
                subscription.updated_at = datetime.utcnow()
                await self.db.commit()
                results["success"].append(tenant_id)
            except Exception as e:
                results["failed"].append({"tenant_id": tenant_id, "error": str(e)})
        
        return results

    async def calculate_prorated_price(
        self,
        tenant_id: str,
        new_plan: str,
    ) -> dict:
        """
        计算升级差价(按剩余天数比例)

        Args:
            tenant_id: 租户ID
            new_plan: 新套餐类型

        Returns:
            {
                "current_plan": "basic",
                "new_plan": "professional",
                "current_plan_value": 150.00,
                "new_plan_value": 300.00,
                "prorated_charge": 150.00,
                "remaining_days": 15
            }
        """
        from decimal import Decimal
        from services.payment_service import PLAN_PRICES

        subscription = await self.get_subscription(tenant_id)

        # 计算剩余天数
        now = datetime.utcnow()
        if subscription.expire_at <= now:
            # 已过期，无法升级
            raise ValueError("订阅已过期，无法升级套餐")

        remaining_days = (subscription.expire_at - now).days

        # 获取当前套餐和新套餐的月价格
        current_price = PLAN_PRICES.get(subscription.plan_type, Decimal("0"))
        new_price = PLAN_PRICES.get(new_plan, Decimal("0"))

        # 如果当前是免费套餐，价格为0
        if subscription.plan_type == "free":
            current_price = Decimal("0")

        # 计算日单价
        current_daily_price = current_price / 30
        new_daily_price = new_price / 30

        # 计算剩余价值
        current_plan_value = current_daily_price * remaining_days
        new_plan_value = new_daily_price * remaining_days

        # 计算差价（升级需要补差价，降级不退款）
        prorated_charge = new_plan_value - current_plan_value

        return {
            "current_plan": subscription.plan_type,
            "new_plan": new_plan,
            "current_plan_value": round(float(current_plan_value), 2),
            "new_plan_value": round(float(new_plan_value), 2),
            "prorated_charge": max(0, round(float(prorated_charge), 2)),  # 不能为负
            "remaining_days": remaining_days
        }


# ===== 服务降级管理器 =====

class DegradationLevel(str, Enum):
    """降级级别"""
    NORMAL = "normal"            # 正常状态
    WARNING = "warning"          # 警告(0天逾期)
    LIMITED = "limited"          # 受限(7天逾期)
    SUSPENDED = "suspended"      # 暂停(15天逾期)
    TERMINATED = "terminated"    # 终止(30天逾期)


class ServiceDegradationManager:
    """服务降级管理器"""

    # 降级策略配置
    DEGRADATION_LEVELS = {
        DegradationLevel.WARNING: {
            "days_overdue": 0,  # 刚过期
            "actions": ["send_warning"],
            "description": "账单已逾期,请及时支付"
        },
        DegradationLevel.LIMITED: {
            "days_overdue": 7,  # 逾期7天
            "actions": ["limit_api_rate", "disable_new_features"],
            "description": "服务受限,部分功能已禁用"
        },
        DegradationLevel.SUSPENDED: {
            "days_overdue": 15,  # 逾期15天
            "actions": ["suspend_service", "readonly_mode"],
            "description": "服务已暂停,仅可查看数据"
        },
        DegradationLevel.TERMINATED: {
            "days_overdue": 30,  # 逾期30天
            "actions": ["terminate_service", "schedule_data_deletion"],
            "description": "服务已终止,数据将在30天后删除"
        }
    }

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis

    async def check_and_degrade(self, tenant_id: str) -> Dict:
        """
        检查并执行降级

        Args:
            tenant_id: 租户ID

        Returns:
            降级结果
        """
        try:
            # 获取租户信息
            tenant = await self._get_tenant(tenant_id)
            if not tenant:
                return {"success": False, "reason": "租户不存在"}

            # 获取欠费账单
            overdue_bills = await self._get_overdue_bills(tenant_id)

            if not overdue_bills:
                # 没有欠费,检查是否需要恢复服务
                if tenant.degradation_level and tenant.degradation_level != DegradationLevel.NORMAL:
                    await self._restore_service(tenant)
                    return {
                        "success": True,
                        "action": "restored",
                        "level": DegradationLevel.NORMAL,
                        "message": "服务已恢复"
                    }
                return {
                    "success": True,
                    "action": "none",
                    "level": DegradationLevel.NORMAL,
                    "message": "服务正常"
                }

            # 计算逾期天数(以最早的账单为准)
            oldest_bill = min(overdue_bills, key=lambda b: b.due_date)
            days_overdue = (datetime.utcnow() - oldest_bill.due_date).days

            # 确定降级级别
            degradation_level = self._determine_level(days_overdue)

            # 如果降级级别发生变化,执行降级
            if degradation_level != tenant.degradation_level:
                await self._apply_degradation(tenant, degradation_level, overdue_bills)
                return {
                    "success": True,
                    "action": "degraded",
                    "level": degradation_level,
                    "days_overdue": days_overdue,
                    "overdue_bills": len(overdue_bills),
                    "message": self.DEGRADATION_LEVELS[degradation_level]["description"]
                }

            return {
                "success": True,
                "action": "unchanged",
                "level": degradation_level,
                "days_overdue": days_overdue,
                "message": "降级级别未变化"
            }

        except Exception as e:
            logger.error(f"检查降级失败: {e}")
            return {"success": False, "error": str(e)}

    async def batch_check_degradation(self) -> Dict:
        """
        批量检查所有租户的降级状态

        Returns:
            批量处理结果
        """
        try:
            # 查询所有活跃租户
            stmt = select(Tenant).where(Tenant.status.in_(["active", "suspended"]))
            result = await self.db.execute(stmt)
            tenants = result.scalars().all()

            degraded_count = 0
            restored_count = 0
            error_count = 0

            for tenant in tenants:
                try:
                    result = await self.check_and_degrade(tenant.tenant_id)
                    if result["success"]:
                        if result["action"] == "degraded":
                            degraded_count += 1
                        elif result["action"] == "restored":
                            restored_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"检查租户降级失败 (tenant={tenant.tenant_id}): {e}")

            return {
                "success": True,
                "total": len(tenants),
                "degraded": degraded_count,
                "restored": restored_count,
                "errors": error_count,
                "message": f"批量检查完成: 降级{degraded_count}, 恢复{restored_count}, 失败{error_count}"
            }

        except Exception as e:
            logger.error(f"批量检查降级失败: {e}")
            return {"success": False, "error": str(e)}

    def _determine_level(self, days_overdue: int) -> DegradationLevel:
        """
        确定降级级别

        Args:
            days_overdue: 逾期天数

        Returns:
            降级级别
        """
        if days_overdue >= 30:
            return DegradationLevel.TERMINATED
        elif days_overdue >= 15:
            return DegradationLevel.SUSPENDED
        elif days_overdue >= 7:
            return DegradationLevel.LIMITED
        elif days_overdue >= 0:
            return DegradationLevel.WARNING
        else:
            return DegradationLevel.NORMAL

    async def _apply_degradation(
        self,
        tenant: Tenant,
        level: DegradationLevel,
        overdue_bills: List[Bill]
    ):
        """
        应用降级策略

        Args:
            tenant: 租户对象
            level: 降级级别
            overdue_bills: 欠费账单列表
        """
        config = self.DEGRADATION_LEVELS[level]

        logger.info(f"应用降级: tenant={tenant.tenant_id}, level={level}")

        # 执行降级动作
        for action in config["actions"]:
            await self._execute_action(tenant, action)

        # 更新租户降级状态
        tenant.degradation_level = level
        tenant.degradation_applied_at = datetime.utcnow()

        # 记录降级原因
        total_overdue = sum(bill.total_amount for bill in overdue_bills)
        tenant.degradation_reason = json.dumps({
            "level": level,
            "overdue_bills": len(overdue_bills),
            "total_overdue": float(total_overdue),
            "oldest_due_date": overdue_bills[0].due_date.isoformat() if overdue_bills else None
        })

        await self.db.commit()

        # 发送降级通知
        await self._send_degradation_notification(tenant, level, overdue_bills)

    async def _execute_action(self, tenant: Tenant, action: str):
        """
        执行降级动作

        Args:
            tenant: 租户对象
            action: 动作名称
        """
        if action == "send_warning":
            # 发送欠费警告
            logger.info(f"发送欠费警告: tenant={tenant.tenant_id}")
            # TODO: 发送邮件/短信通知

        elif action == "limit_api_rate":
            # 限制API速率到10%
            if self.redis:
                await self.redis.set(
                    f"rate_limit_override:{tenant.tenant_id}",
                    "0.1",  # 限制为原速率的10%
                    ex=86400 * 30  # 30天过期
                )
                logger.info(f"限制API速率: tenant={tenant.tenant_id} -> 10%")

        elif action == "disable_new_features":
            # 禁用高级功能,只保留基础功能
            tenant.enabled_features = json.dumps(["BASIC_CHAT"])
            logger.info(f"禁用高级功能: tenant={tenant.tenant_id}")

        elif action == "suspend_service":
            # 暂停服务
            tenant.status = "suspended"
            logger.info(f"暂停服务: tenant={tenant.tenant_id}")

        elif action == "readonly_mode":
            # 只读模式(不能创建新对话,只能查看历史)
            if self.redis:
                await self.redis.set(
                    f"readonly_mode:{tenant.tenant_id}",
                    "1",
                    ex=86400 * 30
                )
                logger.info(f"启用只读模式: tenant={tenant.tenant_id}")

        elif action == "terminate_service":
            # 终止服务
            tenant.status = "terminated"
            logger.info(f"终止服务: tenant={tenant.tenant_id}")

        elif action == "schedule_data_deletion":
            # 计划数据删除(30天后)
            # TODO: 创建数据删除任务
            deletion_date = datetime.utcnow() + timedelta(days=30)
            logger.warning(
                f"计划数据删除: tenant={tenant.tenant_id}, "
                f"deletion_date={deletion_date.isoformat()}"
            )

    async def _restore_service(self, tenant: Tenant):
        """
        恢复服务

        Args:
            tenant: 租户对象
        """
        logger.info(f"恢复服务: tenant={tenant.tenant_id}")

        # 清除Redis中的限制
        if self.redis:
            await self.redis.delete(f"rate_limit_override:{tenant.tenant_id}")
            await self.redis.delete(f"readonly_mode:{tenant.tenant_id}")

        # 恢复租户状态
        tenant.status = "active"
        tenant.degradation_level = DegradationLevel.NORMAL
        tenant.degradation_applied_at = None
        tenant.degradation_reason = None

        # 恢复功能
        subscription_stmt = select(Subscription).where(
            Subscription.tenant_id == tenant.tenant_id
        ).order_by(Subscription.created_at.desc())
        subscription_result = await self.db.execute(subscription_stmt)
        subscription = subscription_result.scalar_one_or_none()

        if subscription:
            plan_config = PLAN_CONFIGS.get(subscription.plan_type, PLAN_CONFIGS["free"])
            tenant.enabled_features = json.dumps([f.value for f in plan_config["features"]])

        await self.db.commit()

        # 发送恢复通知
        await self._send_restoration_notification(tenant)

    async def _get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户信息"""
        stmt = select(Tenant).where(Tenant.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_overdue_bills(self, tenant_id: str) -> List[Bill]:
        """
        获取逾期账单

        Args:
            tenant_id: 租户ID

        Returns:
            逾期账单列表
        """
        now = datetime.utcnow()
        stmt = select(Bill).where(
            and_(
                Bill.tenant_id == tenant_id,
                Bill.status.in_(["pending", "overdue"]),
                Bill.due_date < now
            )
        ).order_by(Bill.due_date)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _send_degradation_notification(
        self,
        tenant: Tenant,
        level: DegradationLevel,
        overdue_bills: List[Bill]
    ):
        """
        发送降级通知

        Args:
            tenant: 租户对象
            level: 降级级别
            overdue_bills: 欠费账单列表
        """
        try:
            total_overdue = sum(bill.total_amount for bill in overdue_bills)

            logger.info(
                f"发送降级通知: tenant={tenant.tenant_id}, "
                f"level={level}, overdue={total_overdue}"
            )

            # TODO: 发送多渠道通知
            # 1. 邮件通知
            # send_email.delay(
            #     to=tenant.contact_email,
            #     subject=f"【{level.upper()}】服务降级通知",
            #     template="service_degradation",
            #     context={
            #         "tenant_id": tenant.tenant_id,
            #         "level": level,
            #         "description": self.DEGRADATION_LEVELS[level]["description"],
            #         "overdue_bills": len(overdue_bills),
            #         "total_overdue": float(total_overdue),
            #         "payment_url": "https://your-domain.com/billing"
            #     }
            # )

            # 2. 站内通知
            # send_in_app_notification.delay(
            #     tenant_id=tenant.tenant_id,
            #     title="服务降级通知",
            #     content=self.DEGRADATION_LEVELS[level]["description"],
            #     urgency="urgent"
            # )

            # 3. 短信通知(SUSPENDED和TERMINATED级别)
            # if level in [DegradationLevel.SUSPENDED, DegradationLevel.TERMINATED]:
            #     send_sms.delay(
            #         phone=tenant.contact_phone,
            #         template="service_degradation_urgent",
            #         params={"level": level}
            #     )

        except Exception as e:
            logger.error(f"发送降级通知失败: {e}")

    async def _send_restoration_notification(self, tenant: Tenant):
        """
        发送服务恢复通知

        Args:
            tenant: 租户对象
        """
        try:
            logger.info(f"发送恢复通知: tenant={tenant.tenant_id}")

            # TODO: 发送通知
            # send_email.delay(
            #     to=tenant.contact_email,
            #     subject="服务已恢复",
            #     template="service_restored",
            #     context={
            #         "tenant_id": tenant.tenant_id,
            #         "restored_at": datetime.utcnow().isoformat()
            #     }
            # )

        except Exception as e:
            logger.error(f"发送恢复通知失败: {e}")
