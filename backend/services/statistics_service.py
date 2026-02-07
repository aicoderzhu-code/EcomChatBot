"""
平台统计服务
"""
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Conversation, Message, Subscription, Tenant
from models.payment import Bill


class StatisticsService:
    """平台统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_statistics(self) -> Dict:
        """
        获取租户统计

        Returns:
            租户统计数据
        """
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 总租户数
        total_stmt = select(func.count(Tenant.id)).where(Tenant.status != "deleted")
        total = await self.db.scalar(total_stmt) or 0

        # 活跃租户（本月有对话）
        active_stmt = (
            select(func.count(func.distinct(Conversation.tenant_id)))
            .select_from(Conversation)
            .where(Conversation.created_at >= month_start)
        )
        active = await self.db.scalar(active_stmt) or 0

        # 试用租户（免费版且活跃）
        trial_stmt = (
            select(func.count(Tenant.id))
            .select_from(Tenant)
            .join(Subscription, Tenant.id == Subscription.tenant_id)
            .where(
                and_(
                    Subscription.plan == "free",
                    Tenant.status == "active",
                )
            )
        )
        trial = await self.db.scalar(trial_stmt) or 0

        # 付费租户（非免费版且订阅活跃）
        paid_stmt = (
            select(func.count(Tenant.id))
            .select_from(Tenant)
            .join(Subscription, Tenant.id == Subscription.tenant_id)
            .where(
                and_(
                    Subscription.plan != "free",
                    Subscription.status == "active",
                )
            )
        )
        paid = await self.db.scalar(paid_stmt) or 0

        # 本月新增
        new_this_month_stmt = select(func.count(Tenant.id)).where(
            and_(
                Tenant.created_at >= month_start,
                Tenant.status != "deleted",
            )
        )
        new_this_month = await self.db.scalar(new_this_month_stmt) or 0

        # 本月流失（订阅过期）
        churned_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "expired",
                Subscription.expired_at >= month_start,
            )
        )
        churned = await self.db.scalar(churned_stmt) or 0

        # 计算流失率
        churn_rate = round(churned / paid * 100, 2) if paid > 0 else 0

        return {
            "total": total,
            "active": active,
            "trial": trial,
            "paid": paid,
            "new_this_month": new_this_month,
            "churned_this_month": churned,
            "churn_rate": churn_rate,
        }

    async def get_revenue_statistics(self) -> Dict:
        """
        获取收入统计

        Returns:
            收入统计数据
        """
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # 本月收入
        this_month_stmt = select(func.sum(Bill.total_amount)).where(
            and_(
                Bill.status == "paid",
                Bill.paid_at >= month_start,
            )
        )
        this_month_revenue = await self.db.scalar(this_month_stmt) or 0

        # 上月收入
        last_month_stmt = select(func.sum(Bill.total_amount)).where(
            and_(
                Bill.status == "paid",
                Bill.paid_at >= last_month_start,
                Bill.paid_at < month_start,
            )
        )
        last_month_revenue = await self.db.scalar(last_month_stmt) or 0

        # MRR (月经常性收入) - 所有活跃订阅的月度价格总和
        mrr_stmt = select(func.sum(Subscription.monthly_price)).where(
            Subscription.status == "active"
        )
        mrr = await self.db.scalar(mrr_stmt) or 0

        # ARR = MRR * 12
        arr = mrr * 12

        # 待收款金额
        pending_stmt = select(func.sum(Bill.total_amount)).where(Bill.status == "pending")
        pending_amount = await self.db.scalar(pending_stmt) or 0

        # 计算增长率
        growth_rate = (
            round((this_month_revenue - last_month_revenue) / last_month_revenue * 100, 2)
            if last_month_revenue > 0
            else 0
        )

        return {
            "this_month": float(this_month_revenue),
            "last_month": float(last_month_revenue),
            "growth_rate": growth_rate,
            "mrr": float(mrr),
            "arr": float(arr),
            "pending_amount": float(pending_amount),
        }

    async def get_usage_statistics(self, redis=None) -> Dict:
        """
        获取用量统计

        Args:
            redis: Redis客户端（可选）

        Returns:
            用量统计数据
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 今日对话数
        today_conversations_stmt = select(func.count(Conversation.id)).where(
            Conversation.created_at >= today_start
        )
        today_conversations = await self.db.scalar(today_conversations_stmt) or 0

        # 本月对话数
        month_conversations_stmt = select(func.count(Conversation.id)).where(
            Conversation.created_at >= month_start
        )
        month_conversations = await self.db.scalar(month_conversations_stmt) or 0

        # 今日消息数
        today_messages_stmt = select(func.count(Message.id)).where(
            Message.created_at >= today_start
        )
        today_messages = await self.db.scalar(today_messages_stmt) or 0

        # 平均响应时间（从Redis获取，如果有的话）
        avg_response_time = 0.0
        active_sessions = 0

        if redis:
            try:
                # 从Redis获取实时指标
                response_time_data = await redis.get("metrics:avg_response_time:today")
                if response_time_data:
                    avg_response_time = float(response_time_data)

                # 获取在线会话数
                active_sessions = await redis.scard("active_sessions") or 0
            except Exception:
                # Redis不可用时，使用默认值
                pass

        return {
            "today_conversations": today_conversations,
            "month_conversations": month_conversations,
            "today_messages": today_messages,
            "avg_response_time_ms": avg_response_time,
            "active_sessions": active_sessions,
        }

    async def get_plan_distribution(self) -> Dict[str, int]:
        """
        获取套餐分布

        Returns:
            套餐分布 {plan: count}
        """
        stmt = (
            select(Subscription.plan, func.count(Subscription.id))
            .where(Subscription.status == "active")
            .group_by(Subscription.plan)
        )

        result = await self.db.execute(stmt)
        distribution = dict(result.all())

        return distribution

    async def get_overview(self, redis=None) -> Dict:
        """
        获取平台统计概览

        Args:
            redis: Redis客户端（可选）

        Returns:
            完整的平台统计数据
        """
        tenant_stats = await self.get_tenant_statistics()
        revenue_stats = await self.get_revenue_statistics()
        usage_stats = await self.get_usage_statistics(redis)
        plan_distribution = await self.get_plan_distribution()

        return {
            "tenant_stats": tenant_stats,
            "revenue_stats": revenue_stats,
            "usage_stats": usage_stats,
            "plan_distribution": plan_distribution,
            "generated_at": datetime.utcnow(),
        }

    async def get_trend_statistics(self, period: str = "30d") -> Dict:
        """
        获取趋势统计

        Args:
            period: 统计周期 (7d/30d/90d)

        Returns:
            趋势统计数据
        """
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)

        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        # 每日新增租户
        new_tenants_stmt = (
            select(
                func.date(Tenant.created_at).label("date"),
                func.count(Tenant.id).label("count"),
            )
            .where(
                and_(
                    Tenant.created_at >= start_date,
                    Tenant.status != "deleted",
                )
            )
            .group_by(func.date(Tenant.created_at))
            .order_by(func.date(Tenant.created_at))
        )

        result = await self.db.execute(new_tenants_stmt)
        new_tenants = [{"date": str(row.date), "count": row.count} for row in result.all()]

        # 每日收入
        daily_revenue_stmt = (
            select(
                func.date(Bill.paid_at).label("date"),
                func.sum(Bill.total_amount).label("amount"),
            )
            .where(
                and_(
                    Bill.paid_at >= start_date,
                    Bill.status == "paid",
                )
            )
            .group_by(func.date(Bill.paid_at))
            .order_by(func.date(Bill.paid_at))
        )

        result = await self.db.execute(daily_revenue_stmt)
        daily_revenue = [
            {"date": str(row.date), "amount": float(row.amount)} for row in result.all()
        ]

        # 每日对话数
        daily_conversations_stmt = (
            select(
                func.date(Conversation.created_at).label("date"),
                func.count(Conversation.id).label("count"),
            )
            .where(Conversation.created_at >= start_date)
            .group_by(func.date(Conversation.created_at))
            .order_by(func.date(Conversation.created_at))
        )

        result = await self.db.execute(daily_conversations_stmt)
        daily_conversations = [
            {"date": str(row.date), "count": row.count} for row in result.all()
        ]

        return {
            "period": period,
            "new_tenants": new_tenants,
            "daily_revenue": daily_revenue,
            "daily_conversations": daily_conversations,
        }
