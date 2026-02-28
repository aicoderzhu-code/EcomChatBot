"""分析报告服务"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import AnalysisReport, Order, ReportStatus
from services.order_analytics.analytics_service import OrderAnalyticsService

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_report(
        self,
        report_type: str,
        title: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> AnalysisReport:
        """创建分析报告"""
        # 根据报告类型设置默认时间范围
        now = datetime.utcnow()
        if not period_end:
            period_end = now
        if not period_start:
            if report_type == "daily":
                period_start = now - timedelta(days=1)
            elif report_type == "weekly":
                period_start = now - timedelta(weeks=1)
            elif report_type == "monthly":
                period_start = now - timedelta(days=30)
            else:
                period_start = now - timedelta(days=30)

        report = AnalysisReport(
            tenant_id=self.tenant_id,
            report_type=report_type,
            title=title,
            status=ReportStatus.PENDING.value,
            period_start=period_start,
            period_end=period_end,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def generate_report(self, report_id: int) -> None:
        """生成报告内容"""
        stmt = select(AnalysisReport).where(
            and_(
                AnalysisReport.id == report_id,
                AnalysisReport.tenant_id == self.tenant_id,
            )
        )
        report = (await self.db.execute(stmt)).scalar_one_or_none()
        if not report:
            return

        report.status = ReportStatus.GENERATING.value
        await self.db.commit()

        try:
            analytics = OrderAnalyticsService(self.db, self.tenant_id)

            # 计算分析期间的天数
            days = 30
            if report.period_start and report.period_end:
                delta = report.period_end - report.period_start
                days = max(delta.days, 1)

            # 获取统计数据
            overview = await analytics.get_overview(days=days)
            top_products = await analytics.get_top_products(days=days)
            buyer_stats = await analytics.get_buyer_stats(days=days)

            # 填充统计数据
            report.statistics = {
                "total_orders": overview["total_orders"],
                "total_revenue": overview["total_revenue"],
                "avg_order_value": overview["avg_order_value"],
                "total_items": overview["total_items"],
                "refund_count": overview["refund_count"],
                "refund_total": overview["refund_total"],
                "status_distribution": overview["status_distribution"],
            }

            # 填充图表数据
            report.charts_data = {
                "daily_trend": overview["daily_trend"],
                "top_products": top_products,
                "buyer_stats": buyer_stats,
            }

            # 生成摘要
            report.summary = self._generate_summary(overview, top_products)

            report.status = ReportStatus.COMPLETED.value
        except Exception as e:
            logger.exception("生成报告失败: %d", report_id)
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)

        await self.db.commit()

    def _generate_summary(self, overview: dict, top_products: list[dict]) -> str:
        """生成报告文本摘要"""
        lines = []
        lines.append(
            f"统计期间共计 {overview['total_orders']} 笔订单，"
            f"总营收 {overview['total_revenue']:.2f} 元，"
            f"平均客单价 {overview['avg_order_value']:.2f} 元。"
        )
        if overview.get("refund_count", 0) > 0:
            lines.append(
                f"退款订单 {overview['refund_count']} 笔，"
                f"退款金额 {overview['refund_total']:.2f} 元。"
            )

        if top_products:
            top = top_products[0]
            lines.append(
                f"热销商品第一名：{top['product_title']}，"
                f"共 {top['order_count']} 笔订单，"
                f"销售额 {top['total_revenue']:.2f} 元。"
            )

        status_dist = overview.get("status_distribution", {})
        if status_dist:
            parts = [f"{k}: {v}笔" for k, v in status_dist.items()]
            lines.append(f"订单状态分布 - {', '.join(parts)}。")

        return "\n".join(lines)

    async def get_report(self, report_id: int) -> AnalysisReport | None:
        """获取报告详情"""
        stmt = select(AnalysisReport).where(
            and_(
                AnalysisReport.id == report_id,
                AnalysisReport.tenant_id == self.tenant_id,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_reports(
        self,
        report_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ):
        """查询报告列表"""
        conditions = [AnalysisReport.tenant_id == self.tenant_id]
        if report_type:
            conditions.append(AnalysisReport.report_type == report_type)
        if status:
            conditions.append(AnalysisReport.status == status)

        count_stmt = select(func.count(AnalysisReport.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AnalysisReport)
            .where(and_(*conditions))
            .order_by(AnalysisReport.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def delete_report(self, report_id: int) -> bool:
        """删除报告"""
        stmt = select(AnalysisReport).where(
            and_(
                AnalysisReport.id == report_id,
                AnalysisReport.tenant_id == self.tenant_id,
            )
        )
        report = (await self.db.execute(stmt)).scalar_one_or_none()
        if not report:
            return False
        await self.db.delete(report)
        await self.db.commit()
        return True
