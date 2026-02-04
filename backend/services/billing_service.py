"""
账单管理服务
"""
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BillNotFoundException
from core.security import generate_tenant_id
from models import Bill, Subscription
from services.subscription_service import SubscriptionService
from services.usage_service import UsageService


class BillingService:
    """账单管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.usage_service = UsageService(db)
        self.subscription_service = SubscriptionService(db)

    async def get_bill(self, bill_id: str) -> Bill:
        """获取账单"""
        stmt = select(Bill).where(Bill.bill_id == bill_id)
        result = await self.db.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise BillNotFoundException(bill_id)

        return bill

    async def list_bills(
        self,
        status: str | None = None,
        period: str | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Bill], int]:
        """查询账单列表"""
        conditions = []
        if status:
            conditions.append(Bill.status == status)
        if period:
            conditions.append(Bill.billing_period == period)
        if tenant_id:
            conditions.append(Bill.tenant_id == tenant_id)

        # 查询总数
        count_stmt = select(func.count(Bill.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        # 分页查询
        stmt = select(Bill).order_by(Bill.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self.db.execute(stmt)
        bills = result.scalars().all()

        return list(bills), total or 0

    async def generate_monthly_bill(self, tenant_id: str, year: int, month: int) -> Bill:
        """
        生成月度账单
        """
        # 获取订阅和用量
        subscription = await self.subscription_service.get_subscription(tenant_id)
        usage_summary = await self.usage_service.get_usage_summary(tenant_id, year, month)

        # 计算费用
        from core.permissions import PLAN_CONFIGS

        plan_config = PLAN_CONFIGS.get(subscription.plan_type, PLAN_CONFIGS["free"])
        base_fee = plan_config["base_price"]
        overage_fee = usage_summary["total_overage_fee"]
        total_amount = base_fee + overage_fee

        # 生成账单
        bill_id = f"bill_{tenant_id}_{year}{month:02d}_{int(datetime.utcnow().timestamp())}"
        billing_period = f"{year}-{month:02d}"

        bill = Bill(
            bill_id=bill_id,
            tenant_id=tenant_id,
            billing_period=billing_period,
            base_fee=base_fee,
            overage_fee=overage_fee,
            discount=0.0,
            adjustment_amount=0.0,
            total_amount=total_amount,
            status="pending",
            due_date=datetime(year, month, 28) if month < 12 else datetime(year + 1, 1, 28),
        )

        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def adjust_bill(
        self,
        bill_id: str,
        adjustment_amount: float,
        reason: str,
    ) -> Bill:
        """调整账单金额"""
        bill = await self.get_bill(bill_id)

        bill.adjustment_amount = adjustment_amount
        bill.adjustment_reason = reason
        bill.total_amount = bill.base_fee + bill.overage_fee + adjustment_amount - bill.discount

        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def mark_as_paid(
        self,
        bill_id: str,
        payment_method: str,
        transaction_id: str | None = None,
    ) -> Bill:
        """标记为已支付"""
        bill = await self.get_bill(bill_id)

        bill.status = "paid"
        bill.payment_method = payment_method
        bill.payment_time = datetime.utcnow()
        bill.transaction_id = transaction_id

        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def get_overdue_bills(self) -> list[Bill]:
        """获取欠费账单"""
        stmt = select(Bill).where(
            Bill.status.in_(["pending", "overdue"]),
            Bill.due_date < datetime.utcnow(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def process_refund(
        self,
        bill_id: str,
        refund_amount: float,
        reason: str,
    ) -> Bill:
        """处理退款"""
        bill = await self.get_bill(bill_id)

        bill.status = "refunded"
        bill.refund_amount = refund_amount
        bill.refund_reason = reason

        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def get_revenue_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """生成收入报表"""
        stmt = (
            select(
                func.sum(Bill.total_amount).label("total_revenue"),
                func.count(Bill.id).label("bill_count"),
                func.avg(Bill.total_amount).label("avg_bill_amount"),
            )
            .where(
                Bill.status == "paid",
                Bill.payment_time >= start_date,
                Bill.payment_time < end_date,
            )
        )

        result = await self.db.execute(stmt)
        row = result.one()

        return {
            "period": {"start": start_date, "end": end_date},
            "total_revenue": row.total_revenue or 0.0,
            "bill_count": row.bill_count or 0,
            "avg_bill_amount": row.avg_bill_amount or 0.0,
        }

    async def calculate_arr_mrr(self) -> dict:
        """计算 ARR 和 MRR"""
        # MRR: 月度经常性收入
        stmt = select(func.sum(Subscription.conversation_quota * 0.0)).where(
            Subscription.status == "active"
        )
        # TODO: 这里需要从PLAN_CONFIGS获取base_price，简化处理
        from core.permissions import PLAN_CONFIGS

        # 获取所有活跃订阅
        stmt = select(Subscription).where(Subscription.status == "active")
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()

        mrr = sum(
            PLAN_CONFIGS.get(sub.plan_type, PLAN_CONFIGS["free"])["base_price"]
            for sub in subscriptions
        )

        # ARR: 年度经常性收入
        arr = mrr * 12

        return {"mrr": mrr, "arr": arr}
