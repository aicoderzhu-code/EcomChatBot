"""自动触发规则服务"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppException, ResourceNotFoundException
from models.conversation import User
from models.order import Order
from models.outreach import OutreachRule, OutreachTask

logger = logging.getLogger(__name__)


class OutreachRuleService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_rule(self, **kwargs) -> OutreachRule:
        rule = OutreachRule(tenant_id=self.tenant_id, **kwargs)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, **kwargs) -> OutreachRule:
        rule = await self._get_rule(rule_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(rule, key, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: int) -> None:
        rule = await self._get_rule(rule_id)
        await self.db.delete(rule)
        await self.db.flush()

    async def list_rules(self, page: int = 1, size: int = 20) -> tuple[list[OutreachRule], int]:
        base = select(OutreachRule).where(OutreachRule.tenant_id == self.tenant_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = base.order_by(OutreachRule.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def toggle_rule(self, rule_id: int) -> OutreachRule:
        rule = await self._get_rule(rule_id)
        rule.is_active = 0 if rule.is_active else 1
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def get_rule_stats(self, rule_id: int) -> dict:
        rule = await self._get_rule(rule_id)
        return {
            "total_triggered": rule.total_triggered,
            "total_converted": rule.total_converted,
            "conversion_rate": round(
                rule.total_converted / max(rule.total_triggered, 1) * 100, 2
            ),
        }

    async def evaluate_rules(self) -> int:
        """评估所有激活规则，创建触达任务。返回创建的任务数。"""
        stmt = select(OutreachRule).where(
            and_(
                OutreachRule.tenant_id == self.tenant_id,
                OutreachRule.is_active == 1,
            )
        )
        result = await self.db.execute(stmt)
        rules = result.scalars().all()

        total_created = 0
        for rule in rules:
            try:
                count = await self._evaluate_single_rule(rule)
                total_created += count
            except Exception as e:
                logger.error(f"规则 {rule.id} 评估失败: {e}")
        return total_created

    async def _evaluate_single_rule(self, rule: OutreachRule) -> int:
        """评估单条规则"""
        conditions = rule.trigger_conditions or {}
        now = datetime.utcnow()
        user_ids = []

        if rule.rule_type == "new_user_inactive":
            # 新用户N天未活跃
            days = conditions.get("inactive_days", 7)
            cutoff = now - timedelta(days=days)
            stmt = select(User.id).where(
                and_(
                    User.tenant_id == self.tenant_id,
                    User.created_at <= cutoff,
                    User.total_conversations <= conditions.get("max_conversations", 1),
                )
            )
            result = await self.db.execute(stmt)
            user_ids = [r[0] for r in result.all()]

        elif rule.rule_type == "churn_risk":
            # 流失风险: N天未对话
            days = conditions.get("inactive_days", 30)
            cutoff = now - timedelta(days=days)
            stmt = select(User.id).where(
                and_(
                    User.tenant_id == self.tenant_id,
                    User.last_conversation_at <= cutoff,
                    User.total_conversations >= conditions.get("min_conversations", 3),
                )
            )
            result = await self.db.execute(stmt)
            user_ids = [r[0] for r in result.all()]

        elif rule.rule_type == "post_purchase":
            # 购买后N天触发
            days = conditions.get("days_after_purchase", 3)
            cutoff_start = now - timedelta(days=days + 1)
            cutoff_end = now - timedelta(days=days)
            stmt = (
                select(Order.buyer_id)
                .where(
                    and_(
                        Order.tenant_id == self.tenant_id,
                        Order.status == "completed",
                        Order.completed_at >= cutoff_start,
                        Order.completed_at <= cutoff_end,
                    )
                )
                .distinct()
            )
            result = await self.db.execute(stmt)
            buyer_ids = [r[0] for r in result.all()]
            if buyer_ids:
                user_stmt = select(User.id).where(
                    and_(
                        User.tenant_id == self.tenant_id,
                        User.platform_user_id.in_(buyer_ids),
                    )
                )
                user_result = await self.db.execute(user_stmt)
                user_ids = [r[0] for r in user_result.all()]

        # 过滤已触发过的用户(冷却期内)
        if user_ids:
            cooldown_cutoff = now - timedelta(hours=rule.cooldown_hours)
            existing_stmt = select(OutreachTask.user_id).where(
                and_(
                    OutreachTask.rule_id == rule.id,
                    OutreachTask.user_id.in_(user_ids),
                    OutreachTask.created_at >= cooldown_cutoff,
                )
            )
            existing = await self.db.execute(existing_stmt)
            existing_user_ids = {r[0] for r in existing.all()}

            # 检查最大触发次数
            if rule.max_triggers_per_user > 0:
                count_stmt = (
                    select(OutreachTask.user_id, func.count(OutreachTask.id))
                    .where(
                        and_(
                            OutreachTask.rule_id == rule.id,
                            OutreachTask.user_id.in_(user_ids),
                        )
                    )
                    .group_by(OutreachTask.user_id)
                    .having(func.count(OutreachTask.id) >= rule.max_triggers_per_user)
                )
                maxed_result = await self.db.execute(count_stmt)
                maxed_user_ids = {r[0] for r in maxed_result.all()}
                existing_user_ids |= maxed_user_ids

            user_ids = [uid for uid in user_ids if uid not in existing_user_ids]

        # 创建任务
        created = 0
        for uid in user_ids:
            task = OutreachTask(
                tenant_id=self.tenant_id,
                rule_id=rule.id,
                user_id=uid,
                platform_type=rule.platform_type,
                platform_config_id=rule.platform_config_id,
                status="pending",
                scheduled_at=now,
            )
            self.db.add(task)
            created += 1

        if created:
            rule.total_triggered += created
            await self.db.flush()
            # 提交异步投递
            from tasks.outreach_tasks import deliver_outreach_task
            for uid in user_ids:
                # 获取刚创建的任务ID
                task_stmt = select(OutreachTask.id).where(
                    and_(
                        OutreachTask.rule_id == rule.id,
                        OutreachTask.user_id == uid,
                        OutreachTask.created_at >= now - timedelta(seconds=10),
                    )
                ).order_by(OutreachTask.id.desc()).limit(1)
                task_result = await self.db.execute(task_stmt)
                task_id = task_result.scalar()
                if task_id:
                    deliver_outreach_task.delay(task_id, self.tenant_id)

        return created

    async def _get_rule(self, rule_id: int) -> OutreachRule:
        stmt = select(OutreachRule).where(
            and_(
                OutreachRule.id == rule_id,
                OutreachRule.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise ResourceNotFoundException("自动规则", str(rule_id))
        return rule
