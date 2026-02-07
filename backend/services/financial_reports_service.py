"""
财务报表服务

提供以下报表功能：
- 收入报表（按时间、套餐、渠道）
- 订阅分析（活跃用户、流失率、留存率）
- 用量统计（趋势、峰值）
- 财务概览（ARR/MRR、增长率）
- 报表导出（CSV/Excel）
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import select, func, and_, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Bill,
    Subscription,
    Tenant,
    UsageRecord,
    PaymentOrder,
    PaymentTransaction,
)
from models.payment import OrderStatus, PaymentChannel, TransactionType
from core.permissions import PLAN_CONFIGS

logger = logging.getLogger(__name__)


class FinancialReportsService:
    """财务报表服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===== 收入报表 =====

    async def get_revenue_summary(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        获取收入概览

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            收入概览数据
        """
        # 总收入
        revenue_stmt = select(
            func.sum(PaymentOrder.amount).label("total_revenue"),
            func.count(PaymentOrder.id).label("order_count"),
        ).where(
            and_(
                PaymentOrder.status == OrderStatus.PAID,
                PaymentOrder.paid_at >= start_date,
                PaymentOrder.paid_at < end_date,
            )
        )
        revenue_result = await self.db.execute(revenue_stmt)
        revenue_row = revenue_result.one()

        # 退款金额
        refund_stmt = select(
            func.sum(PaymentTransaction.amount).label("total_refund"),
            func.count(PaymentTransaction.id).label("refund_count"),
        ).where(
            and_(
                PaymentTransaction.transaction_type == TransactionType.REFUND,
                PaymentTransaction.created_at >= start_date,
                PaymentTransaction.created_at < end_date,
            )
        )
        refund_result = await self.db.execute(refund_stmt)
        refund_row = refund_result.one()

        total_revenue = float(revenue_row.total_revenue or 0)
        total_refund = float(refund_row.total_refund or 0)
        net_revenue = total_revenue - total_refund

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_revenue": total_revenue,
            "total_refund": total_refund,
            "net_revenue": net_revenue,
            "order_count": revenue_row.order_count or 0,
            "refund_count": refund_row.refund_count or 0,
            "avg_order_value": total_revenue / (revenue_row.order_count or 1),
        }

    async def get_revenue_by_plan(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        按套餐类型统计收入

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            各套餐收入数据
        """
        stmt = select(
            PaymentOrder.plan_type,
            func.sum(PaymentOrder.amount).label("revenue"),
            func.count(PaymentOrder.id).label("order_count"),
        ).where(
            and_(
                PaymentOrder.status == OrderStatus.PAID,
                PaymentOrder.paid_at >= start_date,
                PaymentOrder.paid_at < end_date,
            )
        ).group_by(PaymentOrder.plan_type)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "plan_type": row.plan_type,
                "revenue": float(row.revenue or 0),
                "order_count": row.order_count,
                "plan_name": PLAN_CONFIGS.get(row.plan_type, {}).get("name", row.plan_type),
            }
            for row in rows
        ]

    async def get_revenue_by_channel(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        按支付渠道统计收入

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            各渠道收入数据
        """
        stmt = select(
            PaymentOrder.payment_channel,
            func.sum(PaymentOrder.amount).label("revenue"),
            func.count(PaymentOrder.id).label("order_count"),
        ).where(
            and_(
                PaymentOrder.status == OrderStatus.PAID,
                PaymentOrder.paid_at >= start_date,
                PaymentOrder.paid_at < end_date,
            )
        ).group_by(PaymentOrder.payment_channel)

        result = await self.db.execute(stmt)
        rows = result.all()

        channel_names = {
            PaymentChannel.ALIPAY: "支付宝",
            PaymentChannel.WECHAT: "微信支付",
        }

        return [
            {
                "channel": row.payment_channel.value if row.payment_channel else "unknown",
                "channel_name": channel_names.get(row.payment_channel, "未知"),
                "revenue": float(row.revenue or 0),
                "order_count": row.order_count,
            }
            for row in rows
        ]

    async def get_revenue_trend(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day",  # day, week, month
    ) -> List[Dict[str, Any]]:
        """
        获取收入趋势

        Args:
            start_date: 开始日期
            end_date: 结束日期
            granularity: 粒度 (day/week/month)

        Returns:
            收入趋势数据
        """
        if granularity == "month":
            date_trunc = func.date_trunc("month", PaymentOrder.paid_at)
        elif granularity == "week":
            date_trunc = func.date_trunc("week", PaymentOrder.paid_at)
        else:
            date_trunc = func.date_trunc("day", PaymentOrder.paid_at)

        stmt = select(
            date_trunc.label("period"),
            func.sum(PaymentOrder.amount).label("revenue"),
            func.count(PaymentOrder.id).label("order_count"),
        ).where(
            and_(
                PaymentOrder.status == OrderStatus.PAID,
                PaymentOrder.paid_at >= start_date,
                PaymentOrder.paid_at < end_date,
            )
        ).group_by(date_trunc).order_by(date_trunc)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "revenue": float(row.revenue or 0),
                "order_count": row.order_count,
            }
            for row in rows
        ]

    # ===== 订阅分析 =====

    async def get_subscription_overview(self) -> Dict[str, Any]:
        """
        获取订阅概览

        Returns:
            订阅概览数据
        """
        # 各状态订阅数
        status_stmt = select(
            Subscription.status,
            func.count(Subscription.id).label("count"),
        ).group_by(Subscription.status)

        status_result = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in status_result.all()}

        # 各套餐订阅数
        plan_stmt = select(
            Subscription.plan_type,
            func.count(Subscription.id).label("count"),
        ).where(
            Subscription.status == "active"
        ).group_by(Subscription.plan_type)

        plan_result = await self.db.execute(plan_stmt)
        plan_counts = {row.plan_type: row.count for row in plan_result.all()}

        # 即将到期订阅（7天内）
        expiring_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "active",
                Subscription.expire_at <= datetime.utcnow() + timedelta(days=7),
                Subscription.expire_at > datetime.utcnow(),
            )
        )
        expiring_count = await self.db.scalar(expiring_stmt) or 0

        # 计算 MRR
        mrr = sum(
            PLAN_CONFIGS.get(plan, {}).get("base_price", 0) * count
            for plan, count in plan_counts.items()
        )

        return {
            "status_distribution": status_counts,
            "plan_distribution": plan_counts,
            "total_active": status_counts.get("active", 0),
            "total_expired": status_counts.get("expired", 0),
            "expiring_soon": expiring_count,
            "mrr": mrr,
            "arr": mrr * 12,
        }

    async def get_churn_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        获取流失分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            流失分析数据
        """
        # 期初活跃订阅数
        start_active_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.created_at < start_date,
                Subscription.status.in_(["active", "expired"]),
            )
        )
        start_active = await self.db.scalar(start_active_stmt) or 0

        # 期间新增订阅
        new_subs_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.created_at >= start_date,
                Subscription.created_at < end_date,
            )
        )
        new_subscriptions = await self.db.scalar(new_subs_stmt) or 0

        # 期间流失订阅（从active变为expired）
        churned_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "expired",
                Subscription.expired_at >= start_date,
                Subscription.expired_at < end_date,
            )
        )
        churned = await self.db.scalar(churned_stmt) or 0

        # 期末活跃订阅数
        end_active_stmt = select(func.count(Subscription.id)).where(
            Subscription.status == "active"
        )
        end_active = await self.db.scalar(end_active_stmt) or 0

        # 计算流失率
        churn_rate = (churned / start_active * 100) if start_active > 0 else 0
        # 留存率
        retention_rate = 100 - churn_rate

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "start_active": start_active,
            "new_subscriptions": new_subscriptions,
            "churned": churned,
            "end_active": end_active,
            "churn_rate": round(churn_rate, 2),
            "retention_rate": round(retention_rate, 2),
            "net_growth": new_subscriptions - churned,
        }

    async def get_plan_upgrade_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        获取套餐升降级分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            升降级分析数据
        """
        # 从订单中分析升级/降级
        # TODO: 需要在PaymentOrder中记录subscription_type字段
        # 暂时返回占位数据
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "upgrades": 0,
            "downgrades": 0,
            "upgrade_revenue": 0,
            "message": "需要订单中记录subscription_type以支持详细分析",
        }

    # ===== 用量分析 =====

    async def get_usage_overview(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        获取用量概览

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            用量概览数据
        """
        stmt = select(
            func.sum(UsageRecord.conversation_count).label("total_conversations"),
            func.sum(UsageRecord.input_tokens).label("total_input_tokens"),
            func.sum(UsageRecord.output_tokens).label("total_output_tokens"),
            func.sum(UsageRecord.api_calls).label("total_api_calls"),
            func.max(UsageRecord.storage_used).label("max_storage"),
            func.sum(UsageRecord.overage_fee).label("total_overage_fee"),
            func.count(distinct(UsageRecord.tenant_id)).label("active_tenants"),
        ).where(
            and_(
                UsageRecord.record_date >= start_date.date(),
                UsageRecord.record_date < end_date.date(),
            )
        )

        result = await self.db.execute(stmt)
        row = result.one()

        total_tokens = (row.total_input_tokens or 0) + (row.total_output_tokens or 0)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_conversations": row.total_conversations or 0,
            "total_tokens": total_tokens,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_api_calls": row.total_api_calls or 0,
            "max_storage_mb": float(row.max_storage or 0),
            "total_overage_fee": float(row.total_overage_fee or 0),
            "active_tenants": row.active_tenants or 0,
        }

    async def get_usage_trend(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        获取用量趋势

        Args:
            start_date: 开始日期
            end_date: 结束日期
            granularity: 粒度

        Returns:
            用量趋势数据
        """
        if granularity == "month":
            date_trunc = func.date_trunc("month", UsageRecord.record_date)
        elif granularity == "week":
            date_trunc = func.date_trunc("week", UsageRecord.record_date)
        else:
            date_trunc = UsageRecord.record_date

        stmt = select(
            date_trunc.label("period"),
            func.sum(UsageRecord.conversation_count).label("conversations"),
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens).label("tokens"),
            func.sum(UsageRecord.api_calls).label("api_calls"),
        ).where(
            and_(
                UsageRecord.record_date >= start_date.date(),
                UsageRecord.record_date < end_date.date(),
            )
        ).group_by(date_trunc).order_by(date_trunc)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "period": row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period),
                "conversations": row.conversations or 0,
                "tokens": row.tokens or 0,
                "api_calls": row.api_calls or 0,
            }
            for row in rows
        ]

    async def get_top_tenants_by_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取用量最高的租户

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量

        Returns:
            租户用量排行
        """
        stmt = select(
            UsageRecord.tenant_id,
            func.sum(UsageRecord.conversation_count).label("conversations"),
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens).label("tokens"),
            func.sum(UsageRecord.overage_fee).label("overage_fee"),
        ).where(
            and_(
                UsageRecord.record_date >= start_date.date(),
                UsageRecord.record_date < end_date.date(),
            )
        ).group_by(UsageRecord.tenant_id).order_by(
            func.sum(UsageRecord.conversation_count).desc()
        ).limit(limit)

        result = await self.db.execute(stmt)
        rows = result.all()

        # 获取租户信息
        tenant_ids = [row.tenant_id for row in rows]
        if tenant_ids:
            tenant_stmt = select(Tenant).where(Tenant.tenant_id.in_(tenant_ids))
            tenant_result = await self.db.execute(tenant_stmt)
            tenants = {t.tenant_id: t for t in tenant_result.scalars().all()}
        else:
            tenants = {}

        return [
            {
                "tenant_id": row.tenant_id,
                "company_name": tenants.get(row.tenant_id, {}).company_name if row.tenant_id in tenants else "未知",
                "conversations": row.conversations or 0,
                "tokens": row.tokens or 0,
                "overage_fee": float(row.overage_fee or 0),
            }
            for row in rows
        ]

    # ===== 综合报表 =====

    async def get_financial_dashboard(self) -> Dict[str, Any]:
        """
        获取财务仪表盘数据

        Returns:
            仪表盘数据
        """
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)

        # 本月
        month_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            next_month_start = datetime(now.year + 1, 1, 1)
        else:
            next_month_start = datetime(now.year, now.month + 1, 1)

        # 上月
        if now.month == 1:
            last_month_start = datetime(now.year - 1, 12, 1)
            last_month_end = month_start
        else:
            last_month_start = datetime(now.year, now.month - 1, 1)
            last_month_end = month_start

        # 本月收入
        current_month_revenue = await self.get_revenue_summary(month_start, next_month_start)
        # 上月收入
        last_month_revenue = await self.get_revenue_summary(last_month_start, last_month_end)

        # 订阅概览
        subscription_overview = await self.get_subscription_overview()

        # 今日用量
        today_usage = await self.get_usage_overview(today_start, today_start + timedelta(days=1))

        # 本月用量
        month_usage = await self.get_usage_overview(month_start, next_month_start)

        # 计算增长率
        last_month_total = last_month_revenue.get("net_revenue", 0)
        current_month_total = current_month_revenue.get("net_revenue", 0)
        if last_month_total > 0:
            revenue_growth = ((current_month_total - last_month_total) / last_month_total) * 100
        else:
            revenue_growth = 100 if current_month_total > 0 else 0

        return {
            "generated_at": now.isoformat(),
            "revenue": {
                "current_month": current_month_revenue,
                "last_month": last_month_revenue,
                "growth_rate": round(revenue_growth, 2),
            },
            "subscriptions": subscription_overview,
            "usage": {
                "today": today_usage,
                "current_month": month_usage,
            },
        }

    # ===== 报表导出 =====

    async def export_revenue_report_csv(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """
        导出收入报表为CSV

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            CSV内容
        """
        # 获取订单数据
        stmt = select(PaymentOrder).where(
            and_(
                PaymentOrder.status == OrderStatus.PAID,
                PaymentOrder.paid_at >= start_date,
                PaymentOrder.paid_at < end_date,
            )
        ).order_by(PaymentOrder.paid_at)

        result = await self.db.execute(stmt)
        orders = result.scalars().all()

        # 生成CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            "订单号", "租户ID", "套餐类型", "金额", "支付渠道", "支付时间", "状态"
        ])

        # 写入数据
        for order in orders:
            writer.writerow([
                order.order_number,
                order.tenant_id,
                order.plan_type,
                str(order.amount),
                order.payment_channel.value if order.payment_channel else "",
                order.paid_at.isoformat() if order.paid_at else "",
                order.status.value if order.status else "",
            ])

        return output.getvalue()

    async def export_subscription_report_csv(self) -> str:
        """
        导出订阅报表为CSV

        Returns:
            CSV内容
        """
        stmt = select(Subscription).order_by(Subscription.created_at.desc())
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "租户ID", "套餐类型", "状态", "创建时间", "到期时间", "自动续费"
        ])

        for sub in subscriptions:
            writer.writerow([
                sub.tenant_id,
                sub.plan_type,
                sub.status,
                sub.created_at.isoformat() if sub.created_at else "",
                sub.expire_at.isoformat() if sub.expire_at else "",
                "是" if sub.auto_renew else "否",
            ])

        return output.getvalue()

    async def export_usage_report_csv(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """
        导出用量报表为CSV

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            CSV内容
        """
        stmt = select(UsageRecord).where(
            and_(
                UsageRecord.record_date >= start_date.date(),
                UsageRecord.record_date < end_date.date(),
            )
        ).order_by(UsageRecord.record_date, UsageRecord.tenant_id)

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "日期", "租户ID", "对话数", "输入Token", "输出Token", "API调用", "存储使用(MB)", "超额费用"
        ])

        for record in records:
            writer.writerow([
                record.record_date.isoformat(),
                record.tenant_id,
                record.conversation_count,
                record.input_tokens,
                record.output_tokens,
                record.api_calls,
                str(record.storage_used),
                str(record.overage_fee),
            ])

        return output.getvalue()
