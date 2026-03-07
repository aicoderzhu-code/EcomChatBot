"""外呼活动管理服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppException, ResourceNotFoundException
from models.outreach import OutreachCampaign, OutreachTask
from services.customer_segment_service import CustomerSegmentService

logger = logging.getLogger(__name__)


class OutreachService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_campaign(self, **kwargs) -> OutreachCampaign:
        campaign = OutreachCampaign(tenant_id=self.tenant_id, **kwargs)
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def update_campaign(self, campaign_id: int, **kwargs) -> OutreachCampaign:
        campaign = await self._get_campaign(campaign_id)
        if campaign.status not in ("draft", "scheduled"):
            raise AppException("只能修改草稿或已调度的活动", "INVALID_OPERATION")
        for key, value in kwargs.items():
            if value is not None:
                setattr(campaign, key, value)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def list_campaigns(
        self, status: str | None = None, page: int = 1, size: int = 20
    ) -> tuple[list[OutreachCampaign], int]:
        conditions = [OutreachCampaign.tenant_id == self.tenant_id]
        if status:
            conditions.append(OutreachCampaign.status == status)
        base = select(OutreachCampaign).where(and_(*conditions))
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.order_by(OutreachCampaign.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_campaign_detail(self, campaign_id: int) -> OutreachCampaign:
        return await self._get_campaign(campaign_id)

    async def launch_campaign(self, campaign_id: int) -> OutreachCampaign:
        """启动活动 — 生成任务并提交 Celery"""
        campaign = await self._get_campaign(campaign_id)
        if campaign.status not in ("draft", "scheduled"):
            raise AppException("只能启动草稿或已调度的活动", "INVALID_OPERATION")
        if not campaign.segment_id:
            raise AppException("请先选择目标分群", "VALIDATION_ERROR")

        # 获取分群成员
        segment_service = CustomerSegmentService(self.db, self.tenant_id)
        user_ids = await segment_service.get_member_user_ids(campaign.segment_id)
        if not user_ids:
            raise AppException("目标分群没有成员", "VALIDATION_ERROR")

        # 批量创建 OutreachTask
        now = datetime.utcnow()
        for uid in user_ids:
            task = OutreachTask(
                tenant_id=self.tenant_id,
                campaign_id=campaign_id,
                user_id=uid,
                platform_type=campaign.platform_type,
                platform_config_id=campaign.platform_config_id,
                status="pending",
                scheduled_at=campaign.scheduled_at or now,
            )
            self.db.add(task)

        campaign.status = "running"
        campaign.started_at = now
        campaign.total_targets = len(user_ids)
        await self.db.flush()
        await self.db.refresh(campaign)

        # 提交 Celery 批量投递
        from tasks.outreach_tasks import batch_deliver_campaign
        batch_deliver_campaign.delay(campaign_id, self.tenant_id)

        return campaign

    async def pause_campaign(self, campaign_id: int) -> OutreachCampaign:
        campaign = await self._get_campaign(campaign_id)
        if campaign.status != "running":
            raise AppException("只能暂停运行中的活动", "INVALID_OPERATION")
        campaign.status = "paused"
        # 取消未发送的任务
        await self.db.execute(
            update(OutreachTask)
            .where(
                and_(
                    OutreachTask.campaign_id == campaign_id,
                    OutreachTask.status == "pending",
                )
            )
            .values(status="cancelled")
        )
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def resume_campaign(self, campaign_id: int) -> OutreachCampaign:
        campaign = await self._get_campaign(campaign_id)
        if campaign.status != "paused":
            raise AppException("只能恢复已暂停的活动", "INVALID_OPERATION")
        campaign.status = "running"
        # 恢复被取消的任务
        await self.db.execute(
            update(OutreachTask)
            .where(
                and_(
                    OutreachTask.campaign_id == campaign_id,
                    OutreachTask.status == "cancelled",
                )
            )
            .values(status="pending")
        )
        await self.db.flush()
        await self.db.refresh(campaign)
        # 重新提交
        from tasks.outreach_tasks import batch_deliver_campaign
        batch_deliver_campaign.delay(campaign_id, self.tenant_id)
        return campaign

    async def cancel_campaign(self, campaign_id: int) -> OutreachCampaign:
        campaign = await self._get_campaign(campaign_id)
        if campaign.status in ("completed", "failed"):
            raise AppException("活动已结束", "INVALID_OPERATION")
        campaign.status = "failed"
        campaign.completed_at = datetime.utcnow()
        await self.db.execute(
            update(OutreachTask)
            .where(
                and_(
                    OutreachTask.campaign_id == campaign_id,
                    OutreachTask.status.in_(["pending", "generating", "sending"]),
                )
            )
            .values(status="cancelled")
        )
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def get_campaign_stats(self, campaign_id: int) -> dict:
        campaign = await self._get_campaign(campaign_id)
        total = campaign.total_targets or 1
        return {
            "total_targets": campaign.total_targets,
            "sent_count": campaign.sent_count,
            "delivered_count": campaign.delivered_count,
            "failed_count": campaign.failed_count,
            "clicked_count": campaign.clicked_count,
            "converted_count": campaign.converted_count,
            "send_rate": round(campaign.sent_count / total * 100, 2),
            "delivery_rate": round(campaign.delivered_count / max(campaign.sent_count, 1) * 100, 2),
            "conversion_rate": round(campaign.converted_count / total * 100, 2),
        }

    async def get_campaign_tasks(
        self, campaign_id: int, status: str | None = None, page: int = 1, size: int = 20
    ) -> tuple[list[OutreachTask], int]:
        conditions = [OutreachTask.campaign_id == campaign_id]
        if status:
            conditions.append(OutreachTask.status == status)
        base = select(OutreachTask).where(and_(*conditions))
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = base.order_by(OutreachTask.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def _get_campaign(self, campaign_id: int) -> OutreachCampaign:
        stmt = select(OutreachCampaign).where(
            and_(
                OutreachCampaign.id == campaign_id,
                OutreachCampaign.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ResourceNotFoundException("外呼活动", str(campaign_id))
        return campaign
