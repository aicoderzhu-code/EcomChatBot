"""统一内容生成任务管理服务"""
import logging
from datetime import datetime

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.generation import GeneratedAsset, GenerationTask, GenerationTaskStatus
from services.content_generation.image_model_router import ImageModelRouter
from services.content_generation.video_model_router import VideoModelRouter
from services.content_generation.product_prompt_service import ProductPromptService
from services.content_generation.template_service import TemplateService
from services.content_generation.platform_spec_service import PlatformSpecService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


class GenerationService:
    """统一内容生成任务管理"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # task_type → model_type 映射
    _TASK_MODEL_TYPE_MAP = {
        "poster": "image_generation",
        "video": "video_generation",
    }

    async def _resolve_model_config_id(
        self, task_type: str, model_config_id: int | None
    ) -> int | None:
        """模型配置已改用环境变量，此方法保留以兼容旧接口"""
        # 模型配置现在从环境变量读取，不再需要 model_config_id
        return None

    async def create_task(
        self,
        task_type: str,
        prompt: str,
        product_id: int | None = None,
        prompt_id: int | None = None,
        model_config_id: int | None = None,
        params: dict | None = None,
        template_id: int | None = None,
        scene_type: str | None = None,
        target_platform: str | None = None,
        generation_mode: str = "advanced",
    ) -> GenerationTask:
        """创建生成任务"""
        # 解析模型配置：未指定时自动回退到默认模型
        model_config_id = await self._resolve_model_config_id(task_type, model_config_id)

        # 如果使用模板，渲染模板
        final_prompt = prompt
        if template_id:
            template_svc = TemplateService(self.db, self.tenant_id)
            render_result = await template_svc.render_template(
                template_id=template_id,
                product_id=product_id,
                overrides=None,  # 可以从 params 中提取
                target_platform=target_platform,
            )
            final_prompt = render_result["rendered_prompt"]
            # 合并渲染后的参数
            if params is None:
                params = {}
            params.update(render_result["resolved_params"])
            # 增加模板使用次数
            await template_svc.increment_usage(template_id)

        # 如果指定了提示词，使用其内容
        if prompt_id:
            prompt_svc = ProductPromptService(self.db, self.tenant_id)
            product_prompt = await prompt_svc.get_prompt(prompt_id)
            if product_prompt:
                final_prompt = product_prompt.content
                # 如果同时传了手动 prompt，追加为额外要求
                if prompt and prompt != product_prompt.content:
                    final_prompt = f"{final_prompt}\n\n额外要求：{prompt}"
                # 增加使用次数
                await prompt_svc.increment_usage(prompt_id)

        # 如果指定了目标平台，从平台规范获取尺寸
        if target_platform and not template_id:
            platform_svc = PlatformSpecService(self.db)
            # 根据 task_type 推断 media_type
            media_type = "main_image" if task_type == "poster" else "main_video"
            spec = await platform_svc.get_spec(target_platform, media_type)
            if spec and params is None:
                params = {}
            if spec:
                params["size"] = f"{spec.width}x{spec.height}"

        task = GenerationTask(
            tenant_id=self.tenant_id,
            product_id=product_id,
            task_type=task_type,
            status=GenerationTaskStatus.PENDING.value,
            prompt=final_prompt,
            model_config_id=model_config_id,
            prompt_id=prompt_id,
            params=params,
            template_id=template_id,
            scene_type=scene_type,
            target_platform=target_platform,
            generation_mode=generation_mode,
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
            router = ImageModelRouter()
            urls = await router.generate_image(
                prompt=task.prompt,
                params=task.params,
            )
            for url in urls:
                # 下载到 TOS 持久化存储
                try:
                    object_name = await StorageService.download_and_store(
                        url, "images", self.tenant_id
                    )
                    file_url = object_name
                    meta = {"original_url": url}
                except Exception as e:
                    logger.warning("存储失败，使用原始URL: %s", e)
                    file_url = url
                    meta = None
                asset = GeneratedAsset(
                    tenant_id=self.tenant_id,
                    task_id=task.id,
                    product_id=task.product_id,
                    asset_type="image",
                    file_url=file_url,
                    meta_info=meta,
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

        router = VideoModelRouter()
        video_url = await router.generate_video(
            prompt=task.prompt,
            params=task.params,
        )
        # 下载到 TOS 持久化存储
        try:
            object_name = await StorageService.download_and_store(
                video_url, "videos", self.tenant_id
            )
            file_url = object_name
            meta = {"original_url": video_url}
        except Exception as e:
            logger.warning("存储失败，使用原始URL: %s", e)
            file_url = video_url
            meta = None
        asset = GeneratedAsset(
            tenant_id=self.tenant_id,
            task_id=task.id,
            product_id=task.product_id,
            asset_type="video",
            file_url=file_url,
            meta_info=meta,
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
        scene_type: str | None = None,
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
        if scene_type:
            conditions.append(GenerationTask.scene_type == scene_type)

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
        asset_type: str | None = None, keyword: str | None = None,
        is_selected: bool | None = None, scene_type: str | None = None,
        target_platform: str | None = None, review_status: str | None = None,
        page: int = 1, size: int = 20,
    ) -> tuple[list[GeneratedAsset], int]:
        conditions = [GeneratedAsset.tenant_id == self.tenant_id]
        if task_id:
            conditions.append(GeneratedAsset.task_id == task_id)
        if product_id:
            conditions.append(GeneratedAsset.product_id == product_id)
        if asset_type:
            conditions.append(GeneratedAsset.asset_type == asset_type)
        if keyword:
            conditions.append(GeneratedAsset.content.ilike(f"%{keyword}%"))
        if is_selected is not None:
            conditions.append(GeneratedAsset.is_selected == (1 if is_selected else 0))
        if scene_type:
            conditions.append(GeneratedAsset.scene_type == scene_type)
        if target_platform:
            conditions.append(GeneratedAsset.target_platform == target_platform)
        if review_status:
            conditions.append(GeneratedAsset.review_status == review_status)

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

    async def get_asset(self, asset_id: int) -> GeneratedAsset | None:
        stmt = select(GeneratedAsset).where(
            and_(GeneratedAsset.id == asset_id, GeneratedAsset.tenant_id == self.tenant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def delete_asset(self, asset_id: int) -> bool:
        """删除素材（存储文件 + 数据库记录）"""
        asset = await self.get_asset(asset_id)
        if not asset:
            return False
        # 删除存储文件
        if asset.file_url and not asset.file_url.startswith("http"):
            # 只删除存储在TOS的文件（object_name格式）
            try:
                StorageService.delete_object(asset.file_url)
            except Exception as e:
                logger.warning("删除存储文件失败: %s", e)
        await self.db.delete(asset)
        await self.db.commit()
        return True

    async def toggle_asset_selected(self, asset_id: int) -> GeneratedAsset | None:
        """切换素材收藏状态"""
        asset = await self.get_asset(asset_id)
        if not asset:
            return None
        asset.is_selected = 0 if asset.is_selected else 1
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

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

    async def batch_generate(
        self,
        template_id: int,
        product_ids: list[int],
        target_platform: str | None = None,
        params: dict | None = None,
    ) -> list[GenerationTask]:
        """为多个商品使用同一模板批量创建生成任务"""
        template_svc = TemplateService(self.db, self.tenant_id)
        template = await template_svc.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        tasks = []
        for product_id in product_ids:
            task = await self.create_task(
                task_type=template.category,
                prompt="",  # 将由模板渲染
                product_id=product_id,
                template_id=template_id,
                scene_type=template.scene_type,
                target_platform=target_platform,
                generation_mode="simple",
                params=params,
            )
            tasks.append(task)

        return tasks

    async def review_asset(
        self,
        asset_id: int,
        review_status: str,
        note: str | None = None,
    ) -> GeneratedAsset | None:
        """审核素材"""
        asset = await self.get_asset(asset_id)
        if not asset:
            return None

        asset.review_status = review_status
        if note:
            if not asset.meta_info:
                asset.meta_info = {}
            asset.meta_info["review_note"] = note

        await self.db.commit()
        await self.db.refresh(asset)
        return asset

