"""客户分群服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppException, ResourceNotFoundException
from models.conversation import User
from models.customer_segment import CustomerSegment, CustomerSegmentMember
from models.order import Order

logger = logging.getLogger(__name__)


class CustomerSegmentService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_segment(self, **kwargs) -> CustomerSegment:
        segment = CustomerSegment(tenant_id=self.tenant_id, **kwargs)
        self.db.add(segment)
        await self.db.flush()
        await self.db.refresh(segment)
        return segment

    async def update_segment(self, segment_id: int, **kwargs) -> CustomerSegment:
        segment = await self._get_segment(segment_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(segment, key, value)
        await self.db.flush()
        await self.db.refresh(segment)
        return segment

    async def delete_segment(self, segment_id: int) -> None:
        segment = await self._get_segment(segment_id)
        await self.db.execute(
            delete(CustomerSegmentMember).where(CustomerSegmentMember.segment_id == segment_id)
        )
        await self.db.delete(segment)
        await self.db.flush()

    async def list_segments(self, page: int = 1, size: int = 20) -> tuple[list[CustomerSegment], int]:
        base = select(CustomerSegment).where(CustomerSegment.tenant_id == self.tenant_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(CustomerSegment.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_segment_detail(self, segment_id: int) -> CustomerSegment:
        return await self._get_segment(segment_id)

    async def refresh_segment_members(self, segment_id: int) -> CustomerSegment:
        """根据 filter_rules 刷新动态分群成员"""
        segment = await self._get_segment(segment_id)
        if segment.segment_type != "dynamic" or not segment.filter_rules:
            raise AppException("只有动态分群才能刷新成员", "INVALID_OPERATION")

        # 清除旧成员
        await self.db.execute(
            delete(CustomerSegmentMember).where(CustomerSegmentMember.segment_id == segment_id)
        )

        # 构建查询
        user_ids = await self._query_matching_users(segment.filter_rules)

        # 批量插入
        now = datetime.utcnow()
        for uid in user_ids:
            self.db.add(CustomerSegmentMember(segment_id=segment_id, user_id=uid, added_at=now))

        segment.member_count = len(user_ids)
        segment.last_refreshed_at = now
        await self.db.flush()
        await self.db.refresh(segment)
        return segment

    async def get_segment_members(
        self, segment_id: int, page: int = 1, size: int = 20
    ) -> tuple[list[dict], int]:
        """获取分群成员列表"""
        await self._get_segment(segment_id)

        base = (
            select(
                CustomerSegmentMember.id,
                CustomerSegmentMember.user_id,
                CustomerSegmentMember.added_at,
                User.nickname,
                User.vip_level,
                User.total_conversations,
            )
            .join(User, User.id == CustomerSegmentMember.user_id)
            .where(CustomerSegmentMember.segment_id == segment_id)
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(CustomerSegmentMember.id.desc()).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(stmt)).all()
        members = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "nickname": r.nickname,
                "vip_level": r.vip_level,
                "total_conversations": r.total_conversations,
                "added_at": r.added_at,
            }
            for r in rows
        ]
        return members, total

    async def preview_segment(self, filter_rules: dict) -> dict:
        """预览匹配人数"""
        user_ids = await self._query_matching_users(filter_rules)
        # 获取前5个用户作为样本
        sample = []
        if user_ids:
            stmt = select(User.id, User.nickname, User.vip_level).where(
                User.id.in_(user_ids[:5])
            )
            rows = (await self.db.execute(stmt)).all()
            sample = [{"id": r.id, "nickname": r.nickname, "vip_level": r.vip_level} for r in rows]
        return {"matched_count": len(user_ids), "sample_users": sample}

    async def get_member_user_ids(self, segment_id: int) -> list[int]:
        """获取分群所有成员用户ID"""
        stmt = select(CustomerSegmentMember.user_id).where(
            CustomerSegmentMember.segment_id == segment_id
        )
        result = await self.db.execute(stmt)
        return [r[0] for r in result.all()]

    async def add_members(self, segment_id: int, user_ids: list[int]) -> int:
        """手动添加成员到分群"""
        segment = await self._get_segment(segment_id)
        now = datetime.utcnow()
        added = 0
        for uid in user_ids:
            # 检查是否已存在
            exists = await self.db.execute(
                select(CustomerSegmentMember.id).where(
                    and_(
                        CustomerSegmentMember.segment_id == segment_id,
                        CustomerSegmentMember.user_id == uid,
                    )
                )
            )
            if not exists.scalar():
                self.db.add(CustomerSegmentMember(segment_id=segment_id, user_id=uid, added_at=now))
                added += 1
        segment.member_count += added
        await self.db.flush()
        return added

    # ===== Private =====

    async def _get_segment(self, segment_id: int) -> CustomerSegment:
        stmt = select(CustomerSegment).where(
            and_(
                CustomerSegment.id == segment_id,
                CustomerSegment.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        segment = result.scalar_one_or_none()
        if not segment:
            raise ResourceNotFoundException("客户分群", str(segment_id))
        return segment

    async def _query_matching_users(self, filter_rules: dict) -> list[int]:
        """根据筛选条件查询匹配用户"""
        conditions = [User.tenant_id == self.tenant_id]

        if "vip_level" in filter_rules:
            vip = filter_rules["vip_level"]
            if isinstance(vip, dict):
                if "min" in vip:
                    conditions.append(User.vip_level >= vip["min"])
                if "max" in vip:
                    conditions.append(User.vip_level <= vip["max"])
            else:
                conditions.append(User.vip_level >= vip)

        if "last_order_days_ago" in filter_rules:
            # 子查询: 最近N天有订单的用户
            days = filter_rules["last_order_days_ago"]
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            order_subq = (
                select(Order.buyer_id)
                .where(
                    and_(
                        Order.tenant_id == self.tenant_id,
                        Order.created_at >= cutoff,
                    )
                )
                .distinct()
                .subquery()
            )
            conditions.append(User.platform_user_id.in_(select(order_subq.c.buyer_id)))

        if "total_amount" in filter_rules:
            amt = filter_rules["total_amount"]
            amount_subq = (
                select(Order.buyer_id)
                .where(Order.tenant_id == self.tenant_id)
                .group_by(Order.buyer_id)
                .having(func.sum(Order.total_amount) >= amt.get("min", 0))
                .subquery()
            )
            conditions.append(User.platform_user_id.in_(select(amount_subq.c.buyer_id)))

        if "order_count" in filter_rules:
            cnt = filter_rules["order_count"]
            min_count = cnt.get("min", 0) if isinstance(cnt, dict) else cnt
            count_subq = (
                select(Order.buyer_id)
                .where(Order.tenant_id == self.tenant_id)
                .group_by(Order.buyer_id)
                .having(func.count(Order.id) >= min_count)
                .subquery()
            )
            conditions.append(User.platform_user_id.in_(select(count_subq.c.buyer_id)))

        if "platform_type" in filter_rules:
            from models.platform import PlatformConfig
            platform_subq = (
                select(PlatformConfig.id)
                .where(
                    and_(
                        PlatformConfig.tenant_id == self.tenant_id,
                        PlatformConfig.platform_type == filter_rules["platform_type"],
                    )
                )
                .subquery()
            )
            # 用户需要在该平台有对话
            from models.conversation import Conversation
            conv_subq = (
                select(Conversation.user_external_id)
                .where(Conversation.platform_type == filter_rules["platform_type"])
                .distinct()
                .subquery()
            )
            conditions.append(User.user_external_id.in_(select(conv_subq.c.user_external_id)))

        stmt = select(User.id).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return [r[0] for r in result.all()]
