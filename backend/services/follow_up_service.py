"""定时跟进服务"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppException, ResourceNotFoundException
from models.conversation import Conversation, Message, User
from models.follow_up import FollowUpPlan
from models.order import Order
from models.outreach import OutreachTask

logger = logging.getLogger(__name__)


class FollowUpService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_plan(self, **kwargs) -> FollowUpPlan:
        # 设置首次跟进时间
        interval_days = kwargs.get("interval_days", 3)
        plan = FollowUpPlan(
            tenant_id=self.tenant_id,
            next_follow_up_at=datetime.utcnow() + timedelta(days=interval_days),
            **kwargs,
        )
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def list_plans(
        self,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[FollowUpPlan], int]:
        conditions = [FollowUpPlan.tenant_id == self.tenant_id]
        if status:
            conditions.append(FollowUpPlan.status == status)
        base = select(FollowUpPlan).where(and_(*conditions))
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = base.order_by(FollowUpPlan.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_plan(self, plan_id: int) -> FollowUpPlan:
        return await self._get_plan(plan_id)

    async def update_plan(self, plan_id: int, **kwargs) -> FollowUpPlan:
        plan = await self._get_plan(plan_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(plan, key, value)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def cancel_plan(self, plan_id: int) -> FollowUpPlan:
        plan = await self._get_plan(plan_id)
        if plan.status in ("completed", "converted"):
            raise AppException("计划已结束", "INVALID_OPERATION")
        plan.status = "cancelled"
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def execute_follow_up(self, plan_id: int) -> bool:
        """执行一次跟进"""
        plan = await self._get_plan(plan_id)
        if plan.status != "active":
            return False

        now = datetime.utcnow()
        plan.current_step += 1

        # 收集用户上下文
        user_context = await self._collect_user_context(plan.user_id)

        # 构建 AI 上下文
        context = {
            "follow_up_sequence": plan.current_step,
            "reason": plan.reason,
            **(plan.ai_context or {}),
            **user_context,
        }

        # 创建触达任务
        task = OutreachTask(
            tenant_id=self.tenant_id,
            user_id=plan.user_id,
            follow_up_plan_id=plan.id,
            follow_up_sequence=plan.current_step,
            status="pending",
            scheduled_at=now,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)

        # 更新计划进度
        if plan.current_step >= plan.total_steps:
            plan.status = "completed"
            plan.next_follow_up_at = None
        else:
            plan.next_follow_up_at = now + timedelta(days=plan.interval_days)

        await self.db.flush()

        # 提交异步投递
        from tasks.outreach_tasks import deliver_outreach_task
        deliver_outreach_task.delay(task.id, self.tenant_id)

        return True

    async def process_due_follow_ups(self) -> int:
        """处理所有到期的跟进计划"""
        now = datetime.utcnow()
        stmt = select(FollowUpPlan).where(
            and_(
                FollowUpPlan.tenant_id == self.tenant_id,
                FollowUpPlan.status == "active",
                FollowUpPlan.next_follow_up_at <= now,
            )
        )
        result = await self.db.execute(stmt)
        plans = result.scalars().all()

        executed = 0
        for plan in plans:
            try:
                if await self.execute_follow_up(plan.id):
                    executed += 1
            except Exception as e:
                logger.error(f"跟进计划 {plan.id} 执行失败: {e}")
        return executed

    async def get_dashboard(self) -> dict:
        """获取跟进概览"""
        base_cond = FollowUpPlan.tenant_id == self.tenant_id

        active = (await self.db.execute(
            select(func.count()).where(and_(base_cond, FollowUpPlan.status == "active"))
        )).scalar() or 0

        completed = (await self.db.execute(
            select(func.count()).where(and_(base_cond, FollowUpPlan.status == "completed"))
        )).scalar() or 0

        converted = (await self.db.execute(
            select(func.count()).where(and_(base_cond, FollowUpPlan.converted == 1))
        )).scalar() or 0

        # 统计发送的跟进消息数
        total_sent = (await self.db.execute(
            select(func.count()).where(
                and_(
                    OutreachTask.tenant_id == self.tenant_id,
                    OutreachTask.follow_up_plan_id.isnot(None),
                    OutreachTask.status == "sent",
                )
            )
        )).scalar() or 0

        total_plans = active + completed + converted
        return {
            "active_plans": active,
            "completed_plans": completed,
            "converted_plans": converted,
            "total_follow_ups_sent": total_sent,
            "conversion_rate": round(converted / max(total_plans, 1) * 100, 2),
        }

    async def _collect_user_context(self, user_id: int) -> dict:
        """收集用户上下文供AI使用"""
        context: dict = {}

        # 用户信息
        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if user:
            context["user_nickname"] = user.nickname
            context["user_vip_level"] = user.vip_level

        # 最近订单
        order_stmt = (
            select(Order)
            .where(and_(Order.tenant_id == self.tenant_id))
            .order_by(Order.id.desc())
            .limit(3)
        )
        if user and user.platform_user_id:
            order_stmt = order_stmt.where(Order.buyer_id == user.platform_user_id)
        orders = (await self.db.execute(order_stmt)).scalars().all()
        if orders:
            context["recent_orders"] = [
                {"product": o.product_title, "amount": float(o.total_amount), "status": o.status}
                for o in orders
            ]

        # 最近对话摘要
        if user:
            conv_stmt = (
                select(Message.content)
                .join(Conversation, Conversation.conversation_id == Message.conversation_id)
                .where(
                    and_(
                        Conversation.tenant_id == self.tenant_id,
                        Conversation.user_external_id == user.user_external_id,
                        Message.role == "user",
                    )
                )
                .order_by(Message.id.desc())
                .limit(5)
            )
            msgs = (await self.db.execute(conv_stmt)).scalars().all()
            if msgs:
                context["recent_messages"] = list(msgs)

        return context

    async def _get_plan(self, plan_id: int) -> FollowUpPlan:
        stmt = select(FollowUpPlan).where(
            and_(
                FollowUpPlan.id == plan_id,
                FollowUpPlan.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise ResourceNotFoundException("跟进计划", str(plan_id))
        return plan
