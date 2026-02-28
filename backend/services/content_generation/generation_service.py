"""统一内容生成任务管理服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.generation import GeneratedAsset, GenerationTask, GenerationTaskStatus
from models.product import Product
from services.content_generation.image_model_router import ImageModelRouter
from services.content_generation.video_model_router import VideoModelRouter
from services.content_generation.prompt_template_service import PromptTemplateService

logger = logging.getLogger(__name__)


class GenerationService:
    """统一内容生成任务管理"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_task(
        self,
        task_type: str,
        prompt: str,
        product_id: int | None = None,
        template_id: int | None = None,
        model_config_id: int | None = None,
        params: dict | None = None,
    ) -> GenerationTask:
        """创建生成任务"""
        # 如果有模板，渲染提示词
        final_prompt = prompt
        if template_id:
            template_svc = PromptTemplateService(self.db, self.tenant_id)
            template = await template_svc.get_template(template_id)
            if template:
                # 获取商品信息作为变量
                variables = {}
                if product_id:
                    product = (await self.db.execute(
                        select(Product).where(Product.id == product_id)
                    )).scalar_one_or_none()
                    if product:
                        variables = {
                            "product_title": product.title,
                            "product_description": product.description or "",
                            "product_price": str(product.price),
                            "product_category": product.category or "",
                        }
                final_prompt = PromptTemplateService.render_template(
                    template.content, variables
                )
                # 追加用户自定义 prompt
                if prompt and prompt != template.content:
                    final_prompt = f"{final_prompt}\n\n额外要求：{prompt}"
                # 增加使用次数
                template.usage_count += 1

        task = GenerationTask(
            tenant_id=self.tenant_id,
            product_id=product_id,
            task_type=task_type,
            status=GenerationTaskStatus.PENDING.value,
            prompt=final_prompt,
            model_config_id=model_config_id,
            template_id=template_id,
            params=params,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def execute_task(self, task_id: int) -> None:
        """执行生成任务（由 Celery 调用）"""
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        task = (await self.db.execute(stmt)).scalar_one_or_none()
        if not task:
            logger.error("生成任务不存在: %d", task_id)
            return

        task.status = GenerationTaskStatus.PROCESSING.value
        task.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            if task.task_type in ("poster", "title", "description"):
                await self._execute_image_or_text(task)
            elif task.task_type == "video":
                await self._execute_video(task)

            task.status = GenerationTaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
        except Exception as e:
            logger.exception("生成任务失败: %d", task_id)
            task.status = GenerationTaskStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()

        await self.db.commit()

    async def _execute_image_or_text(self, task: GenerationTask) -> None:
        """执行图像或文案生成"""
        if task.task_type == "poster" and task.model_config_id:
            # 图像生成
            router = ImageModelRouter(self.db, self.tenant_id)
            urls = await router.generate_image(
                prompt=task.prompt,
                model_config_id=task.model_config_id,
                params=task.params,
            )
            for url in urls:
                asset = GeneratedAsset(
                    tenant_id=self.tenant_id,
                    task_id=task.id,
                    product_id=task.product_id,
                    asset_type="image",
                    file_url=url,
                )
                self.db.add(asset)
            task.result_count = len(urls)
        else:
            # 文案生成 (title/description) - 使用 LLM
            from services.llm_service import LLMService
            llm_service = LLMService(tenant_id=self.tenant_id)
            result = await llm_service.generate_response(
                messages=[{"role": "user", "content": task.prompt}]
            )
            asset = GeneratedAsset(
                tenant_id=self.tenant_id,
                task_id=task.id,
                product_id=task.product_id,
                asset_type="text",
                content=result,
            )
            self.db.add(asset)
            task.result_count = 1

        await self.db.flush()

    async def _execute_video(self, task: GenerationTask) -> None:
        """执行视频生成"""
        if not task.model_config_id:
            raise ValueError("视频生成需要指定模型配置")

        router = VideoModelRouter(self.db, self.tenant_id)
        video_url = await router.generate_video(
            prompt=task.prompt,
            model_config_id=task.model_config_id,
            params=task.params,
        )
        asset = GeneratedAsset(
            tenant_id=self.tenant_id,
            task_id=task.id,
            product_id=task.product_id,
            asset_type="video",
            file_url=video_url,
        )
        self.db.add(asset)
        task.result_count = 1
        await self.db.flush()

    async def get_task(self, task_id: int) -> GenerationTask | None:
        stmt = select(GenerationTask).where(
            and_(GenerationTask.id == task_id, GenerationTask.tenant_id == self.tenant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_tasks(
        self,
        task_type: str | None = None,
        product_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[GenerationTask], int]:
        conditions = [GenerationTask.tenant_id == self.tenant_id]
        if task_type:
            conditions.append(GenerationTask.task_type == task_type)
        if product_id:
            conditions.append(GenerationTask.product_id == product_id)
        if status:
            conditions.append(GenerationTask.status == status)

        count_stmt = select(func.count(GenerationTask.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(GenerationTask)
            .where(and_(*conditions))
            .order_by(GenerationTask.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        tasks = list(result.scalars().all())
        return tasks, total

    async def list_assets(
        self, task_id: int | None = None, product_id: int | None = None,
        asset_type: str | None = None, page: int = 1, size: int = 20,
    ) -> tuple[list[GeneratedAsset], int]:
        conditions = [GeneratedAsset.tenant_id == self.tenant_id]
        if task_id:
            conditions.append(GeneratedAsset.task_id == task_id)
        if product_id:
            conditions.append(GeneratedAsset.product_id == product_id)
        if asset_type:
            conditions.append(GeneratedAsset.asset_type == asset_type)

        count_stmt = select(func.count(GeneratedAsset.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(GeneratedAsset)
            .where(and_(*conditions))
            .order_by(GeneratedAsset.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        assets = list(result.scalars().all())
        return assets, total

    async def retry_task(self, task_id: int) -> GenerationTask | None:
        """重试失败的任务"""
        task = await self.get_task(task_id)
        if not task or task.status != GenerationTaskStatus.FAILED.value:
            return None
        task.status = GenerationTaskStatus.PENDING.value
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        await self.db.commit()
        await self.db.refresh(task)
        return task
