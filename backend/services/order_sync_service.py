"""订单同步服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order
from models.platform import PlatformConfig
from models.product import PlatformSyncTask, SyncTarget, SyncTaskStatus, SyncType
from services.platform.adapter_factory import create_adapter

logger = logging.getLogger(__name__)


class OrderSyncService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def trigger_sync(
        self, platform_config_id: int, start_time=None, end_time=None
    ) -> PlatformSyncTask:
        """触发订单同步任务"""
        # 检查是否已有运行中的任务
        stmt = select(PlatformSyncTask).where(
            and_(
                PlatformSyncTask.tenant_id == self.tenant_id,
                PlatformSyncTask.platform_config_id == platform_config_id,
                PlatformSyncTask.sync_target == SyncTarget.ORDER.value,
                PlatformSyncTask.status.in_(
                    [SyncTaskStatus.PENDING.value, SyncTaskStatus.RUNNING.value]
                ),
            )
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError("已有正在运行的订单同步任务")

        task = PlatformSyncTask(
            tenant_id=self.tenant_id,
            platform_config_id=platform_config_id,
            sync_target=SyncTarget.ORDER.value,
            sync_type=SyncType.FULL.value,
            status=SyncTaskStatus.PENDING.value,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def execute_sync(self, task_id: int) -> None:
        """执行订单同步"""
        stmt = select(PlatformSyncTask).where(PlatformSyncTask.id == task_id)
        task = (await self.db.execute(stmt)).scalar_one_or_none()
        if not task:
            return

        config = (
            await self.db.execute(
                select(PlatformConfig).where(
                    PlatformConfig.id == task.platform_config_id
                )
            )
        ).scalar_one_or_none()
        if not config:
            task.status = SyncTaskStatus.FAILED.value
            task.error_message = "平台配置不存在"
            await self.db.commit()
            return

        task.status = SyncTaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            adapter = create_adapter(config)
            page = 1
            total_synced = 0
            total_failed = 0
            while True:
                result = await adapter.fetch_orders(page=page, page_size=50)
                task.total_count = result.total
                for dto in result.items:
                    try:
                        await self._upsert_order(config.id, dto)
                        total_synced += 1
                    except Exception as e:
                        logger.error("同步订单失败 %s: %s", dto.platform_order_id, e)
                        total_failed += 1
                task.synced_count = total_synced
                task.failed_count = total_failed
                await self.db.commit()
                if page * 50 >= result.total:
                    break
                page += 1
            task.status = SyncTaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
        except Exception as e:
            logger.exception("订单同步任务失败: %d", task_id)
            task.status = SyncTaskStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
        await self.db.commit()

    async def _upsert_order(self, platform_config_id: int, dto) -> Order:
        """插入或更新订单"""
        stmt = select(Order).where(
            and_(
                Order.tenant_id == self.tenant_id,
                Order.platform_config_id == platform_config_id,
                Order.platform_order_id == dto.platform_order_id,
            )
        )
        order = (await self.db.execute(stmt)).scalar_one_or_none()
        if order:
            order.status = dto.status
            order.total_amount = dto.total_amount
            order.paid_at = dto.paid_at
            order.shipped_at = dto.shipped_at
            order.completed_at = dto.completed_at
            order.refund_amount = dto.refund_amount
            order.platform_data = dto.platform_data
        else:
            order = Order(
                tenant_id=self.tenant_id,
                platform_config_id=platform_config_id,
                platform_order_id=dto.platform_order_id,
                product_title=dto.product_title,
                buyer_id=dto.buyer_id,
                quantity=dto.quantity,
                unit_price=dto.unit_price,
                total_amount=dto.total_amount,
                status=dto.status,
                paid_at=dto.paid_at,
                shipped_at=dto.shipped_at,
                platform_data=dto.platform_data,
            )
            self.db.add(order)
        await self.db.flush()
        return order

    async def list_orders(
        self,
        status: str | None = None,
        platform_config_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        size: int = 20,
    ):
        """查询订单列表"""
        conditions = [Order.tenant_id == self.tenant_id]
        if status:
            conditions.append(Order.status == status)
        if platform_config_id:
            conditions.append(Order.platform_config_id == platform_config_id)
        if keyword:
            conditions.append(
                (Order.platform_order_id.ilike(f"%{keyword}%"))
                | (Order.product_title.ilike(f"%{keyword}%"))
            )

        count_stmt = select(func.count(Order.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_order(self, order_id: int) -> Order | None:
        """获取订单详情"""
        stmt = select(Order).where(
            and_(Order.id == order_id, Order.tenant_id == self.tenant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
