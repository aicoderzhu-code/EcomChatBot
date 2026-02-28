"""商品同步服务"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeBase
from models.platform import PlatformConfig
from models.product import (
    PlatformSyncTask, Product, ProductSyncSchedule,
    SyncTaskStatus, SyncTarget, SyncType,
)
from services.knowledge_service import KnowledgeService
from services.platform.adapter_factory import create_adapter

logger = logging.getLogger(__name__)


class ProductSyncService:
    """商品同步服务

    负责从电商平台拉取商品数据，写入 Product 表，
    并自动生成知识库条目。
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ===== 商品 CRUD =====

    async def list_products(
        self,
        keyword: str | None = None,
        category: str | None = None,
        status: str | None = None,
        platform_config_id: int | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Product], int]:
        """查询商品列表"""
        conditions = [Product.tenant_id == self.tenant_id]
        if keyword:
            conditions.append(Product.title.ilike(f"%{keyword}%"))
        if category:
            conditions.append(Product.category == category)
        if status:
            conditions.append(Product.status == status)
        if platform_config_id:
            conditions.append(Product.platform_config_id == platform_config_id)

        # 总数
        count_stmt = select(func.count(Product.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # 分页
        stmt = (
            select(Product)
            .where(and_(*conditions))
            .order_by(Product.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        return products, total

    async def get_product(self, product_id: int) -> Product | None:
        """获取商品详情"""
        stmt = select(Product).where(
            and_(Product.id == product_id, Product.tenant_id == self.tenant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ===== 同步逻辑 =====

    async def trigger_sync(
        self, platform_config_id: int, sync_type: str = "full"
    ) -> PlatformSyncTask:
        """触发同步任务"""
        # 检查是否有正在运行的同步任务
        stmt = select(PlatformSyncTask).where(
            and_(
                PlatformSyncTask.tenant_id == self.tenant_id,
                PlatformSyncTask.platform_config_id == platform_config_id,
                PlatformSyncTask.sync_target == SyncTarget.PRODUCT.value,
                PlatformSyncTask.status.in_([
                    SyncTaskStatus.PENDING.value,
                    SyncTaskStatus.RUNNING.value,
                ]),
            )
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError("已有正在运行的同步任务，请等待完成后再试")

        task = PlatformSyncTask(
            tenant_id=self.tenant_id,
            platform_config_id=platform_config_id,
            sync_target=SyncTarget.PRODUCT.value,
            sync_type=sync_type,
            status=SyncTaskStatus.PENDING.value,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def execute_sync(self, task_id: int) -> None:
        """执行同步任务（由 Celery Task 调用）"""
        stmt = select(PlatformSyncTask).where(PlatformSyncTask.id == task_id)
        task = (await self.db.execute(stmt)).scalar_one_or_none()
        if not task:
            logger.error("同步任务不存在: %d", task_id)
            return

        # 获取平台配置
        config_stmt = select(PlatformConfig).where(
            PlatformConfig.id == task.platform_config_id
        )
        config = (await self.db.execute(config_stmt)).scalar_one_or_none()
        if not config:
            task.status = SyncTaskStatus.FAILED.value
            task.error_message = "平台配置不存在"
            await self.db.commit()
            return

        # 更新任务状态
        task.status = SyncTaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            adapter = create_adapter(config)

            if task.sync_type == SyncType.FULL.value:
                await self._full_sync(adapter, config.id, task)
            else:
                await self._incremental_sync(adapter, config.id, task)

            task.status = SyncTaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
        except Exception as e:
            logger.exception("同步任务失败: %d", task_id)
            task.status = SyncTaskStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()

        await self.db.commit()

    async def _full_sync(
        self, adapter, platform_config_id: int, task: PlatformSyncTask
    ) -> None:
        """全量同步"""
        page = 1
        page_size = 50
        total_synced = 0
        total_failed = 0

        while True:
            result = await adapter.fetch_products(page=page, page_size=page_size)
            task.total_count = result.total

            for dto in result.items:
                try:
                    await self._upsert_product(platform_config_id, dto)
                    total_synced += 1
                except Exception as e:
                    logger.error("同步商品失败 %s: %s", dto.platform_product_id, e)
                    total_failed += 1

            task.synced_count = total_synced
            task.failed_count = total_failed
            await self.db.commit()

            if page * page_size >= result.total:
                break
            page += 1

    async def _incremental_sync(
        self, adapter, platform_config_id: int, task: PlatformSyncTask
    ) -> None:
        """增量同步"""
        # 获取上次同步时间
        schedule_stmt = select(ProductSyncSchedule).where(
            and_(
                ProductSyncSchedule.tenant_id == self.tenant_id,
                ProductSyncSchedule.platform_config_id == platform_config_id,
            )
        )
        schedule = (await self.db.execute(schedule_stmt)).scalar_one_or_none()
        since = schedule.last_run_at if schedule and schedule.last_run_at else (
            datetime.utcnow() - timedelta(hours=1)
        )

        updated_products = await adapter.fetch_updated_products(since)
        task.total_count = len(updated_products)

        total_synced = 0
        total_failed = 0
        for dto in updated_products:
            try:
                await self._upsert_product(platform_config_id, dto)
                total_synced += 1
            except Exception as e:
                logger.error("增量同步商品失败 %s: %s", dto.platform_product_id, e)
                total_failed += 1

        task.synced_count = total_synced
        task.failed_count = total_failed

        # 更新调度时间
        if schedule:
            schedule.last_run_at = datetime.utcnow()
            schedule.next_run_at = datetime.utcnow() + timedelta(minutes=schedule.interval_minutes)

    async def _upsert_product(self, platform_config_id: int, dto) -> Product:
        """新增或更新商品"""
        stmt = select(Product).where(
            and_(
                Product.tenant_id == self.tenant_id,
                Product.platform_config_id == platform_config_id,
                Product.platform_product_id == dto.platform_product_id,
            )
        )
        product = (await self.db.execute(stmt)).scalar_one_or_none()

        if product:
            # 更新
            product.title = dto.title
            product.description = dto.description
            product.price = dto.price
            product.original_price = dto.original_price
            product.category = dto.category
            product.images = dto.images
            product.videos = dto.videos
            product.attributes = dto.attributes
            product.sales_count = dto.sales_count
            product.stock = dto.stock
            product.status = dto.status
            product.platform_data = dto.platform_data
            product.last_synced_at = datetime.utcnow()
        else:
            # 新建
            product = Product(
                tenant_id=self.tenant_id,
                platform_config_id=platform_config_id,
                platform_product_id=dto.platform_product_id,
                title=dto.title,
                description=dto.description,
                price=dto.price,
                original_price=dto.original_price,
                category=dto.category,
                images=dto.images,
                videos=dto.videos,
                attributes=dto.attributes,
                sales_count=dto.sales_count,
                stock=dto.stock,
                status=dto.status,
                platform_data=dto.platform_data,
                last_synced_at=datetime.utcnow(),
            )
            self.db.add(product)

        await self.db.flush()

        # 自动生成/更新知识库条目
        await self._sync_to_knowledge_base(product)

        return product

    async def _sync_to_knowledge_base(self, product: Product) -> None:
        """将商品信息同步到知识库"""
        # 格式化商品知识内容
        content_parts = [
            f"商品名称：{product.title}",
            f"价格：{product.price}元",
        ]
        if product.original_price:
            content_parts.append(f"原价：{product.original_price}元")
        if product.category:
            content_parts.append(f"分类：{product.category}")
        if product.description:
            content_parts.append(f"描述：{product.description}")
        if product.attributes:
            content_parts.append(f"规格：{product.attributes}")
        content_parts.append(f"库存：{product.stock}")
        content_parts.append(f"销量：{product.sales_count}")

        content = "\n".join(content_parts)

        if product.knowledge_base_id:
            # 更新已有知识库条目
            await self.db.execute(
                sa_update(KnowledgeBase)
                .where(KnowledgeBase.id == product.knowledge_base_id)
                .values(
                    title=product.title,
                    content=content,
                    category=product.category,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            # 创建新的知识库条目
            knowledge_service = KnowledgeService(self.db, self.tenant_id)
            kb = await knowledge_service.create_knowledge(
                knowledge_type="product",
                title=product.title,
                content=content,
                category=product.category,
                tags=["商品", "自动同步"],
            )
            product.knowledge_base_id = kb.id

    # ===== 同步调度 =====

    async def get_sync_schedule(self, platform_config_id: int) -> ProductSyncSchedule | None:
        """获取同步调度配置"""
        stmt = select(ProductSyncSchedule).where(
            and_(
                ProductSyncSchedule.tenant_id == self.tenant_id,
                ProductSyncSchedule.platform_config_id == platform_config_id,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_sync_schedule(
        self,
        platform_config_id: int,
        interval_minutes: int | None = None,
        is_active: bool | None = None,
    ) -> ProductSyncSchedule:
        """创建或更新同步调度配置"""
        schedule = await self.get_sync_schedule(platform_config_id)

        if not schedule:
            schedule = ProductSyncSchedule(
                tenant_id=self.tenant_id,
                platform_config_id=platform_config_id,
                interval_minutes=interval_minutes or 60,
                is_active=1 if is_active is not False else 0,
                next_run_at=datetime.utcnow() + timedelta(minutes=interval_minutes or 60),
            )
            self.db.add(schedule)
        else:
            if interval_minutes is not None:
                schedule.interval_minutes = interval_minutes
            if is_active is not None:
                schedule.is_active = 1 if is_active else 0
            if interval_minutes:
                schedule.next_run_at = datetime.utcnow() + timedelta(minutes=interval_minutes)

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    # ===== 同步任务查询 =====

    async def list_sync_tasks(
        self, platform_config_id: int | None = None, page: int = 1, size: int = 20
    ) -> tuple[list[PlatformSyncTask], int]:
        """查询同步任务列表"""
        conditions = [
            PlatformSyncTask.tenant_id == self.tenant_id,
            PlatformSyncTask.sync_target == SyncTarget.PRODUCT.value,
        ]
        if platform_config_id:
            conditions.append(PlatformSyncTask.platform_config_id == platform_config_id)

        count_stmt = select(func.count(PlatformSyncTask.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(PlatformSyncTask)
            .where(and_(*conditions))
            .order_by(PlatformSyncTask.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        tasks = list(result.scalars().all())

        return tasks, total
