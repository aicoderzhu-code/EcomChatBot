"""内容模板服务"""
import re
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_template import ContentTemplate, PlatformMediaSpec
from models.product import Product


class TemplateService:
    """内容模板服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def list_templates(
        self,
        category: str | None = None,
        scene_type: str | None = None,
        platform: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ContentTemplate], int]:
        """查询模板列表（系统模板 + 租户自定义模板）"""
        query = select(ContentTemplate).where(
            ContentTemplate.is_active == 1,
            or_(
                ContentTemplate.tenant_id == self.tenant_id,
                ContentTemplate.tenant_id.is_(None)  # 系统模板
            )
        )

        # 过滤条件
        if category:
            query = query.where(ContentTemplate.category == category)
        if scene_type:
            query = query.where(ContentTemplate.scene_type == scene_type)
        if platform and platform != "all":
            # 平台过滤：检查 platform_presets JSON 字段
            query = query.where(
                func.json_extract_path_text(
                    ContentTemplate.platform_presets, platform
                ).isnot(None)
            )

        # 排序
        query = query.order_by(
            ContentTemplate.is_system.desc(),  # 系统模板优先
            ContentTemplate.sort_order.asc(),
            ContentTemplate.usage_count.desc()
        )

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        templates = list(result.scalars().all())

        return templates, total

    async def get_template(self, template_id: int) -> ContentTemplate | None:
        """获取模板详情"""
        query = select(ContentTemplate).where(
            ContentTemplate.id == template_id,
            ContentTemplate.is_active == 1,
            or_(
                ContentTemplate.tenant_id == self.tenant_id,
                ContentTemplate.tenant_id.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def render_template(
        self,
        template_id: int,
        product_id: int | None = None,
        overrides: dict | None = None,
        target_platform: str | None = None,
    ) -> dict[str, Any]:
        """核心方法：模板变量替换

        Args:
            template_id: 模板ID
            product_id: 商品ID（可选）
            overrides: 用户自定义变量值（可选）
            target_platform: 目标平台（可选）

        Returns:
            {
                "rendered_prompt": str,  # 渲染后的提示词
                "resolved_params": dict,  # 解析后的参数（含尺寸等）
                "variables_used": dict    # 变量填充详情
            }
        """
        # 1. 获取模板
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # 2. 准备变量值字典
        variables_used = {}
        product_data = {}

        # 如果有 product_id，读取商品数据
        if product_id:
            product = await self._get_product(product_id)
            if product:
                product_data = {
                    "title": product.title,
                    "price": product.price,
                    "category": product.category,
                    "description": product.description or "",
                    "attributes": product.attributes or {},
                }

        # 3. 根据 variables 定义填充变量值
        if template.variables:
            for var_def in template.variables:
                key = var_def.get("key")
                source = var_def.get("source")
                required = var_def.get("required", False)
                default = var_def.get("default")

                value = None

                # 优先使用 overrides
                if overrides and key in overrides:
                    value = overrides[key]
                # 从商品数据提取
                elif source and source.startswith("product."):
                    field_name = source.replace("product.", "")
                    value = product_data.get(field_name)
                # 使用默认值
                elif default:
                    value = default

                # 检查必填项
                if required and not value:
                    raise ValueError(f"Required variable '{key}' is missing")

                if value:
                    variables_used[key] = str(value)

        # 4. 替换提示词中的变量占位符
        rendered_prompt = template.prompt_template
        for key, value in variables_used.items():
            rendered_prompt = rendered_prompt.replace(f"{{{{{key}}}}}", value)

        # 5. 解析参数（尺寸、平台规范等）
        resolved_params = template.default_params.copy() if template.default_params else {}

        # 如果指定了目标平台，从 platform_presets 或 platform_media_specs 获取尺寸
        if target_platform and template.platform_presets:
            platform_preset = template.platform_presets.get(target_platform)
            if platform_preset:
                resolved_params.update(platform_preset)

        return {
            "rendered_prompt": rendered_prompt,
            "resolved_params": resolved_params,
            "variables_used": variables_used,
        }

    async def create_template(
        self,
        name: str,
        category: str,
        scene_type: str,
        prompt_template: str,
        variables: list[dict] | None = None,
        style_options: list[str] | None = None,
        platform_presets: dict | None = None,
        default_params: dict | None = None,
        thumbnail_url: str | None = None,
    ) -> ContentTemplate:
        """创建租户自定义模板"""
        template = ContentTemplate(
            tenant_id=self.tenant_id,
            name=name,
            category=category,
            scene_type=scene_type,
            prompt_template=prompt_template,
            variables=variables,
            style_options=style_options,
            platform_presets=platform_presets,
            default_params=default_params,
            thumbnail_url=thumbnail_url,
            is_system=0,
            is_active=1,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def increment_usage(self, template_id: int) -> None:
        """增加模板使用次数"""
        template = await self.get_template(template_id)
        if template:
            template.usage_count += 1
            await self.db.commit()

    async def _get_product(self, product_id: int) -> Product | None:
        """获取商品数据"""
        query = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == self.tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


