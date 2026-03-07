"""平台规范服务"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_template import PlatformMediaSpec


class PlatformSpecService:
    """平台媒体规范服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_specs(
        self,
        platform_type: str | None = None,
        media_type: str | None = None,
    ) -> list[PlatformMediaSpec]:
        """查询平台规范列表"""
        query = select(PlatformMediaSpec)

        if platform_type:
            query = query.where(PlatformMediaSpec.platform_type == platform_type)
        if media_type:
            query = query.where(PlatformMediaSpec.media_type == media_type)

        query = query.order_by(
            PlatformMediaSpec.platform_type,
            PlatformMediaSpec.media_type
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_spec(
        self,
        platform_type: str,
        media_type: str,
    ) -> PlatformMediaSpec | None:
        """获取特定平台和媒体类型的规范"""
        query = select(PlatformMediaSpec).where(
            PlatformMediaSpec.platform_type == platform_type,
            PlatformMediaSpec.media_type == media_type
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def resolve_size_for_platform(
        self,
        platform_type: str,
        media_type: str,
        provider_capabilities: dict,
    ) -> str | None:
        """将平台要求的尺寸匹配到最接近的 provider 支持尺寸

        Args:
            platform_type: 平台类型
            media_type: 媒体类型
            provider_capabilities: Provider 能力字典（含支持的尺寸列表）

        Returns:
            最接近的尺寸字符串（如 "1024x1024"）或 None
        """
        # 这个方法可以在后续实现更复杂的匹配逻辑
        # 目前简化处理：直接返回平台规范的尺寸
        return None  # 占位实现
