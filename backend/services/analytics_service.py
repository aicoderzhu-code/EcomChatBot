"""
运营分析服务
"""
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Conversation, Message, Subscription, Tenant
from models.tenant import Bill


class AnalyticsService:
    """运营分析服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_growth_analysis(self, months: int = 12) -> Dict:
        """
        租户增长分析

        Args:
            months: 统计月数

        Returns:
            {
                "monthly_data": [
                    {
                        "month": "2026-01",
                        "new": 10,
                        "churned": 2,
                        "net": 8,
                        "cumulative": 100,
                        "growth_rate": 8.7
                    },
                    ...
                ],
                "total_growth": 50,
                "avg_monthly_growth": 4.2
            }
        """
        end_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=30 * months)

        monthly_data = []
        current_month = start_date

        while current_month < end_date:
            next_month = (current_month + timedelta(days=32)).replace(day=1)

            # 新增租户
            new_tenants_stmt = select(func.count(Tenant.id)).where(
                and_(
                    Tenant.created_at >= current_month,
                    Tenant.created_at < next_month,
                    Tenant.status != "deleted",
                )
            )
            new_tenants = await self.db.scalar(new_tenants_stmt) or 0

            # 流失租户（订阅过期且未续费）
            churned_stmt = select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "expired",
                    Subscription.expired_at >= current_month,
                    Subscription.expired_at < next_month,
                )
            )
            churned = await self.db.scalar(churned_stmt) or 0

            # 累计活跃租户
            cumulative_stmt = select(func.count(Tenant.id)).where(
                and_(
                    Tenant.created_at < next_month,
                    Tenant.status == "active",
                )
            )
            cumulative = await self.db.scalar(cumulative_stmt) or 0

            monthly_data.append(
                {
                    "month": current_month.strftime("%Y-%m"),
                    "new": new_tenants,
                    "churned": churned,
                    "net": new_tenants - churned,
                    "cumulative": cumulative,
                }
            )

            current_month = next_month

        # 计算增长率
        for i in range(1, len(monthly_data)):
            prev = monthly_data[i - 1]["cumulative"]
            curr = monthly_data[i]["cumulative"]
            monthly_data[i]["growth_rate"] = round((curr - prev) / prev * 100, 2) if prev > 0 else 0

        return {
            "monthly_data": monthly_data,
            "total_growth": (
                monthly_data[-1]["cumulative"] - monthly_data[0]["cumulative"]
                if monthly_data
                else 0
            ),
            "avg_monthly_growth": (
                sum(d["net"] for d in monthly_data) / len(monthly_data) if monthly_data else 0
            ),
        }

    async def get_churn_analysis(self, months: int = 6) -> Dict:
        """
        流失分析

        Args:
            months: 统计月数

        Returns:
            {
                "monthly_churn": [
                    {
                        "month": "2026-01",
                        "start_count": 100,
                        "churned": 5,
                        "churn_rate": 5.0
                    },
                    ...
                ],
                "avg_churn_rate": 4.5,
                "at_risk_tenants": [...]
            }
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)

        # 月度流失率
        monthly_churn = []
        current_month = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        while current_month < end_date:
            next_month = (current_month + timedelta(days=32)).replace(day=1)

            # 月初活跃付费租户
            start_paid_stmt = select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "active",
                    Subscription.plan != "free",
                    Subscription.created_at < current_month,
                )
            )
            start_paid = await self.db.scalar(start_paid_stmt) or 0

            # 本月流失
            churned_stmt = select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "expired",
                    Subscription.expired_at >= current_month,
                    Subscription.expired_at < next_month,
                )
            )
            churned = await self.db.scalar(churned_stmt) or 0

            churn_rate = round(churned / start_paid * 100, 2) if start_paid > 0 else 0

            monthly_churn.append(
                {
                    "month": current_month.strftime("%Y-%m"),
                    "start_count": start_paid,
                    "churned": churned,
                    "churn_rate": churn_rate,
                }
            )

            current_month = next_month

        # 流失风险预警（30天内到期且活跃度低）
        warning_threshold = end_date + timedelta(days=30)
        at_risk_stmt = (
            select(Tenant, Subscription)
            .join(Subscription, Tenant.id == Subscription.tenant_id)
            .where(
                and_(
                    Subscription.expire_at <= warning_threshold,
                    Subscription.expire_at > end_date,
                    Subscription.auto_renew == False,
                )
            )
        )

        result = await self.db.execute(at_risk_stmt)
        at_risk_rows = result.all()

        at_risk_list = []
        for tenant, subscription in at_risk_rows:
            # 计算活跃度（最近30天对话数）
            recent_conversations_stmt = select(func.count(Conversation.id)).where(
                and_(
                    Conversation.tenant_id == tenant.tenant_id,
                    Conversation.created_at >= end_date - timedelta(days=30),
                )
            )
            recent_conversations = await self.db.scalar(recent_conversations_stmt) or 0

            at_risk_list.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "company_name": tenant.company_name,
                    "plan": subscription.plan,
                    "expires_at": subscription.expire_at.isoformat(),
                    "days_until_expiry": (subscription.expire_at - end_date).days,
                    "recent_activity": recent_conversations,
                    "risk_level": "high" if recent_conversations < 10 else "medium",
                }
            )

        return {
            "monthly_churn": monthly_churn,
            "avg_churn_rate": (
                sum(d["churn_rate"] for d in monthly_churn) / len(monthly_churn)
                if monthly_churn
                else 0
            ),
            "at_risk_tenants": sorted(at_risk_list, key=lambda x: x["days_until_expiry"]),
        }

    async def calculate_ltv(self, tenant_id: str | None = None) -> List[Dict]:
        """
        计算客户生命周期价值(LTV)

        LTV = 平均月收入 × 预期客户生命周期(月)

        Args:
            tenant_id: 租户ID（可选，不指定则计算所有租户）

        Returns:
            [
                {
                    "tenant_id": "TID001",
                    "ltv": 5000.00,
                    "months_active": 12,
                    "total_revenue": 2400.00,
                    "avg_monthly_revenue": 200.00
                },
                ...
            ]
        """
        query = select(Tenant).where(Tenant.status != "deleted")

        if tenant_id:
            query = query.where(Tenant.tenant_id == tenant_id)

        result = await self.db.execute(query)
        tenants = result.scalars().all()

        ltv_data = []

        for tenant in tenants:
            # 计算总收入
            total_revenue_stmt = select(func.sum(Bill.total_amount)).where(
                and_(
                    Bill.tenant_id == tenant.tenant_id,
                    Bill.status == "paid",
                )
            )
            total_revenue = await self.db.scalar(total_revenue_stmt) or 0

            # 计算活跃月数
            first_payment_stmt = select(func.min(Bill.paid_at)).where(
                and_(
                    Bill.tenant_id == tenant.tenant_id,
                    Bill.status == "paid",
                )
            )
            first_payment = await self.db.scalar(first_payment_stmt)

            if first_payment:
                months_active = max(1, (datetime.utcnow() - first_payment).days // 30)
            else:
                months_active = max(1, (datetime.utcnow() - tenant.created_at).days // 30)

            avg_monthly = total_revenue / months_active if months_active > 0 else 0

            # 预测LTV（假设平均客户生命周期24个月）
            expected_lifetime = 24
            ltv = avg_monthly * expected_lifetime

            ltv_data.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "company_name": tenant.company_name,
                    "ltv": round(ltv, 2),
                    "months_active": months_active,
                    "total_revenue": float(total_revenue),
                    "avg_monthly_revenue": round(avg_monthly, 2),
                }
            )

        return sorted(ltv_data, key=lambda x: x["ltv"], reverse=True)

    async def identify_high_value_tenants(self, top_n: int = 20) -> List[Dict]:
        """
        识别高价值租户

        评分维度：
        - 收入贡献 (40%)
        - 活跃度 (30%)
        - 增长潜力 (20%)
        - 客户忠诚度 (10%)

        Args:
            top_n: 返回前N个高价值租户

        Returns:
            [
                {
                    "tenant_id": "TID001",
                    "company_name": "测试公司",
                    "plan": "professional",
                    "value_score": 85.5,
                    "score_breakdown": {...},
                    "insights": [...]
                },
                ...
            ]
        """
        stmt = select(Tenant).where(Tenant.status == "active")
        result = await self.db.execute(stmt)
        tenants = result.scalars().all()

        scored_tenants = []

        for tenant in tenants:
            score = await self._calculate_value_score(tenant)
            
            # 获取订阅信息
            sub_stmt = select(Subscription).where(Subscription.tenant_id == tenant.tenant_id)
            sub_result = await self.db.execute(sub_stmt)
            subscription = sub_result.scalar_one_or_none()
            
            scored_tenants.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "company_name": tenant.company_name,
                    "plan": subscription.plan if subscription else "free",
                    "value_score": score["total"],
                    "score_breakdown": score["breakdown"],
                    "insights": score["insights"],
                }
            )

        # 按分数排序
        scored_tenants.sort(key=lambda x: x["value_score"], reverse=True)

        return scored_tenants[:top_n]

    async def _calculate_value_score(self, tenant: Tenant) -> Dict:
        """计算租户价值分数"""
        now = datetime.utcnow()

        # 1. 收入贡献分数 (0-40)
        total_revenue_stmt = select(func.sum(Bill.total_amount)).where(
            and_(
                Bill.tenant_id == tenant.tenant_id,
                Bill.status == "paid",
            )
        )
        total_revenue = await self.db.scalar(total_revenue_stmt) or 0

        revenue_score = min(40, total_revenue / 1000 * 4)  # 每1000元4分

        # 2. 活跃度分数 (0-30)
        monthly_conversations_stmt = select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant.tenant_id,
                Conversation.created_at >= now - timedelta(days=30),
            )
        )
        monthly_conversations = await self.db.scalar(monthly_conversations_stmt) or 0

        activity_score = min(30, monthly_conversations / 100 * 30)  # 100次对话满分

        # 3. 增长潜力分数 (0-20)
        # 基于套餐升级空间
        sub_stmt = select(Subscription).where(Subscription.tenant_id == tenant.tenant_id)
        sub_result = await self.db.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()
        
        plan_order = {"free": 0, "basic": 1, "professional": 2, "enterprise": 3}
        current_plan = subscription.plan if subscription else "free"
        upgrade_potential = (3 - plan_order.get(current_plan, 0)) * 5

        growth_score = min(20, upgrade_potential + 5)  # 基础5分

        # 4. 忠诚度分数 (0-10)
        months_as_customer = (now - tenant.created_at).days // 30
        loyalty_score = min(10, months_as_customer)  # 每月1分，最多10分

        total = revenue_score + activity_score + growth_score + loyalty_score

        insights = []
        if revenue_score >= 30:
            insights.append("高收入贡献客户")
        if activity_score >= 25:
            insights.append("高活跃度用户")
        if upgrade_potential >= 10:
            insights.append("有升级潜力")
        if loyalty_score >= 8:
            insights.append("忠诚老客户")

        return {
            "total": round(total, 2),
            "breakdown": {
                "revenue": round(revenue_score, 2),
                "activity": round(activity_score, 2),
                "growth": round(growth_score, 2),
                "loyalty": round(loyalty_score, 2),
            },
            "insights": insights,
        }

    async def get_cohort_analysis(self, months: int = 6) -> Dict:
        """
        队列分析（留存率）

        按注册月份分组，追踪每个队列在后续月份的留存情况

        Args:
            months: 分析的队列数（最近N个月的注册队列）

        Returns:
            {
                "cohorts": [
                    {
                        "cohort_month": "2026-01",
                        "total_tenants": 50,
                        "retention_rates": {
                            "0": 100.0,  # 注册当月
                            "1": 85.0,   # 第1个月后
                            "2": 75.0,   # 第2个月后
                            ...
                        }
                    },
                    ...
                ]
            }
        """
        end_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=30 * months)

        cohorts = []
        current_month = start_date

        while current_month < end_date:
            next_month = (current_month + timedelta(days=32)).replace(day=1)

            # 获取该月注册的租户
            cohort_tenants_stmt = select(Tenant.tenant_id).where(
                and_(
                    Tenant.created_at >= current_month,
                    Tenant.created_at < next_month,
                    Tenant.status != "deleted",
                )
            )
            result = await self.db.execute(cohort_tenants_stmt)
            cohort_tenant_ids = [row[0] for row in result.all()]

            if not cohort_tenant_ids:
                current_month = next_month
                continue

            total_tenants = len(cohort_tenant_ids)

            # 计算各月份的留存率
            retention_rates = {"0": 100.0}  # 注册当月留存率为100%

            # 追踪后续每个月的留存情况
            for offset in range(1, (end_date.year - next_month.year) * 12 + (end_date.month - next_month.month) + 1):
                check_month = (next_month + timedelta(days=32 * offset)).replace(day=1)
                check_month_end = (check_month + timedelta(days=32)).replace(day=1)

                # 该月仍然活跃的租户数（有对话记录或订阅仍活跃）
                retained_stmt = select(func.count(func.distinct(Tenant.id))).select_from(Tenant).where(
                    and_(
                        Tenant.tenant_id.in_(cohort_tenant_ids),
                        Tenant.status == "active",
                    )
                )
                retained_count = await self.db.scalar(retained_stmt) or 0

                retention_rate = round(retained_count / total_tenants * 100, 2) if total_tenants > 0 else 0
                retention_rates[str(offset)] = retention_rate

            cohorts.append(
                {
                    "cohort_month": current_month.strftime("%Y-%m"),
                    "total_tenants": total_tenants,
                    "retention_rates": retention_rates,
                }
            )

            current_month = next_month

        return {"cohorts": cohorts}

