"""素材上传到平台服务"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.generation import GeneratedAsset
from models.platform import PlatformConfig
from services.platform.adapter_factory import create_adapter

logger = logging.getLogger(__name__)


class AssetUploadService:
    """将生成的素材上传到电商平台"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def upload_to_platform(
        self, asset_id: int, platform_config_id: int
    ) -> str:
        """上传素材到指定平台，返回平台侧URL"""
        # 获取素材
        asset = (await self.db.execute(
            select(GeneratedAsset).where(GeneratedAsset.id == asset_id)
        )).scalar_one_or_none()
        if not asset:
            raise ValueError("素材不存在")

        # 获取平台配置
        config = (await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.id == platform_config_id)
        )).scalar_one_or_none()
        if not config:
            raise ValueError("平台配置不存在")

        adapter = create_adapter(config)

        product_id = str(asset.product_id) if asset.product_id else ""

        if asset.asset_type == "image" and asset.file_url:
            platform_url = await adapter.upload_image(product_id, asset.file_url)
        elif asset.asset_type == "video" and asset.file_url:
            platform_url = await adapter.upload_video(product_id, asset.file_url)
        else:
            raise ValueError(f"不支持上传的资产类型: {asset.asset_type}")

        # 更新素材记录
        asset.platform_url = platform_url
        await self.db.commit()

        return platform_url
