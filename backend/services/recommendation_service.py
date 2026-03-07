"""推荐规则管理服务"""
import logging

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ResourceNotFoundException
from models.recommendation import RecommendationLog, RecommendationRule

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_rule(self, **kwargs) -> RecommendationRule:
        rule = RecommendationRule(tenant_id=self.tenant_id, **kwargs)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, **kwargs) -> RecommendationRule:
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

    async def list_rules(self, page: int = 1, size: int = 20) -> tuple[list[RecommendationRule], int]:
        base = select(RecommendationRule).where(RecommendationRule.tenant_id == self.tenant_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = base.order_by(RecommendationRule.priority.desc(), RecommendationRule.id.desc()).offset(
            (page - 1) * size
        ).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_rule(self, rule_id: int) -> RecommendationRule:
        return await self._get_rule(rule_id)

    async def list_logs(
        self,
        user_id: int | None = None,
        order_id: int | None = None,
        conversation_id: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[RecommendationLog], int]:
        conditions = [RecommendationLog.tenant_id == self.tenant_id]
        if user_id:
            conditions.append(RecommendationLog.user_id == user_id)
        if order_id:
            conditions.append(RecommendationLog.trigger_order_id == order_id)
        if conversation_id:
            conditions.append(RecommendationLog.conversation_id == conversation_id)

        base = select(RecommendationLog).where(and_(*conditions))
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = base.order_by(RecommendationLog.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_stats(self) -> dict:
        cond = RecommendationLog.tenant_id == self.tenant_id
        total = (await self.db.execute(select(func.count()).where(cond))).scalar() or 0
        displayed = (await self.db.execute(
            select(func.count()).where(and_(cond, RecommendationLog.displayed == 1))
        )).scalar() or 0
        clicked = (await self.db.execute(
            select(func.count()).where(and_(cond, RecommendationLog.clicked_product_id.isnot(None)))
        )).scalar() or 0
        converted = (await self.db.execute(
            select(func.count()).where(and_(cond, RecommendationLog.converted == 1))
        )).scalar() or 0

        return {
            "total_recommendations": total,
            "total_displayed": displayed,
            "total_clicked": clicked,
            "total_converted": converted,
            "click_rate": round(clicked / max(displayed, 1) * 100, 2),
            "conversion_rate": round(converted / max(total, 1) * 100, 2),
        }

    async def _get_rule(self, rule_id: int) -> RecommendationRule:
        stmt = select(RecommendationRule).where(
            and_(
                RecommendationRule.id == rule_id,
                RecommendationRule.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise ResourceNotFoundException("推荐规则", str(rule_id))
        return rule
