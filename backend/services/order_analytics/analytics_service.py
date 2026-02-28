"""订单分析服务"""
from datetime import datetime, timedelta

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order


class OrderAnalyticsService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def get_overview(self, days: int = 30) -> dict:
        """获取订单概览统计"""
        since = datetime.utcnow() - timedelta(days=days)
        conditions = [Order.tenant_id == self.tenant_id, Order.created_at >= since]

        # 基础统计
        stats_stmt = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_revenue"),
            func.avg(Order.total_amount).label("avg_order_value"),
            func.sum(Order.quantity).label("total_items"),
        ).where(and_(*conditions))
        result = (await self.db.execute(stats_stmt)).one()

        # 状态分布
        status_stmt = (
            select(Order.status, func.count(Order.id))
            .where(and_(*conditions))
            .group_by(Order.status)
        )
        status_dist = {
            row[0]: row[1] for row in (await self.db.execute(status_stmt)).all()
        }

        # 日趋势
        daily_stmt = (
            select(
                func.date(Order.created_at).label("date"),
                func.count(Order.id).label("orders"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .where(and_(*conditions))
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        daily_data = [
            {
                "date": str(row.date),
                "orders": row.orders,
                "revenue": float(row.revenue or 0),
            }
            for row in (await self.db.execute(daily_stmt)).all()
        ]

        # 退款统计
        refund_stmt = select(
            func.count(Order.id).label("refund_count"),
            func.sum(Order.refund_amount).label("refund_total"),
        ).where(
            and_(
                Order.tenant_id == self.tenant_id,
                Order.created_at >= since,
                Order.status == "refunded",
            )
        )
        refund_result = (await self.db.execute(refund_stmt)).one()

        return {
            "total_orders": result.total_orders or 0,
            "total_revenue": float(result.total_revenue or 0),
            "avg_order_value": round(float(result.avg_order_value or 0), 2),
            "total_items": result.total_items or 0,
            "status_distribution": status_dist,
            "daily_trend": daily_data,
            "refund_count": refund_result.refund_count or 0,
            "refund_total": float(refund_result.refund_total or 0),
        }

    async def get_top_products(
        self, days: int = 30, limit: int = 10
    ) -> list[dict]:
        """获取热销商品排行"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                Order.product_title,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("total_revenue"),
                func.sum(Order.quantity).label("total_quantity"),
            )
            .where(
                and_(
                    Order.tenant_id == self.tenant_id,
                    Order.created_at >= since,
                    Order.product_title != "",
                )
            )
            .group_by(Order.product_title)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "product_title": row.product_title,
                "order_count": row.order_count,
                "total_revenue": float(row.total_revenue or 0),
                "total_quantity": row.total_quantity,
            }
            for row in result.all()
        ]

    async def get_buyer_stats(self, days: int = 30, limit: int = 10) -> list[dict]:
        """获取买家统计"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                Order.buyer_id,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("total_spent"),
            )
            .where(
                and_(
                    Order.tenant_id == self.tenant_id,
                    Order.created_at >= since,
                    Order.buyer_id != "",
                )
            )
            .group_by(Order.buyer_id)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "buyer_id": row.buyer_id,
                "order_count": row.order_count,
                "total_spent": float(row.total_spent or 0),
            }
            for row in result.all()
        ]
