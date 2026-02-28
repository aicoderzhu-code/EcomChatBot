"""图像生成模型路由器 - 根据 provider 路由到不同的图像生成 API"""
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.model_config import ModelConfig

logger = logging.getLogger(__name__)


class ImageModelRouter:
    """图像生成模型路由器"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def _get_model_config(self, model_config_id: int) -> ModelConfig | None:
        stmt = select(ModelConfig).where(
            ModelConfig.id == model_config_id,
            ModelConfig.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_image(
        self,
        prompt: str,
        model_config_id: int,
        params: dict | None = None,
    ) -> list[str]:
        """生成图像，返回图像URL列表"""
        config = await self._get_model_config(model_config_id)
        if not config:
            raise ValueError("模型配置不存在")

        provider = config.provider
        handlers = {
            "openai": self._generate_openai,
            "zhipuai": self._generate_zhipuai,
            "siliconflow": self._generate_siliconflow,
        }

        handler = handlers.get(provider)
        if not handler:
            raise ValueError(f"不支持的图像生成提供商: {provider}")

        return await handler(config, prompt, params or {})

    async def _generate_openai(self, config: ModelConfig, prompt: str, params: dict) -> list[str]:
        """OpenAI DALL-E API"""
        api_base = config.api_base or "https://api.openai.com/v1"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{api_base}/images/generations",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "n": params.get("n", 1),
                    "size": params.get("size", "1024x1024"),
                    "response_format": "url",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["url"] for item in data.get("data", [])]

    async def _generate_zhipuai(self, config: ModelConfig, prompt: str, params: dict) -> list[str]:
        """智谱AI CogView API"""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://open.bigmodel.cn/api/paas/v4/images/generations",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "size": params.get("size", "1024x1024"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["url"] for item in data.get("data", [])]

    async def _generate_siliconflow(self, config: ModelConfig, prompt: str, params: dict) -> list[str]:
        """硅基流动图像生成"""
        api_base = config.api_base or "https://api.siliconflow.cn/v1"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{api_base}/images/generations",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "n": params.get("n", 1),
                    "image_size": params.get("size", "1024x1024"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item.get("url", "") for item in data.get("images", data.get("data", []))]
