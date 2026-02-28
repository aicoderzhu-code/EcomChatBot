"""视频生成模型路由器 - 根据 provider 路由到不同的视频生成 API"""
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.model_config import ModelConfig

logger = logging.getLogger(__name__)


class VideoModelRouter:
    """视频生成模型路由器"""

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

    async def generate_video(
        self,
        prompt: str,
        model_config_id: int,
        params: dict | None = None,
    ) -> str:
        """生成视频，返回视频URL"""
        config = await self._get_model_config(model_config_id)
        if not config:
            raise ValueError("模型配置不存在")

        provider = config.provider
        handlers = {
            "zhipuai": self._generate_zhipuai,
            "siliconflow": self._generate_siliconflow,
        }

        handler = handlers.get(provider)
        if not handler:
            raise ValueError(f"不支持的视频生成提供商: {provider}")

        return await handler(config, prompt, params or {})

    async def _generate_zhipuai(self, config: ModelConfig, prompt: str, params: dict) -> str:
        """智谱AI CogVideoX API"""
        body: dict = {
            "model": config.model_name,
            "prompt": prompt,
            "image_url": params.get("image_url"),
        }
        if params.get("duration"):
            body["duration"] = params["duration"]
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                "https://open.bigmodel.cn/api/paas/v4/videos/generations",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            # 智谱返回任务ID，需要轮询获取结果
            task_id = data.get("id", "")
            return await self._poll_zhipuai_video(config, task_id)

    async def _poll_zhipuai_video(self, config: ModelConfig, task_id: str) -> str:
        """轮询智谱AI视频生成结果"""
        import asyncio
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):  # 最多等待5分钟
                resp = await client.get(
                    f"https://open.bigmodel.cn/api/paas/v4/async-result/{task_id}",
                    headers={"Authorization": f"Bearer {config.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("task_status", "")
                if status == "SUCCESS":
                    video_results = data.get("video_result", [])
                    if video_results:
                        return video_results[0].get("url", "")
                    return ""
                elif status == "FAIL":
                    raise Exception(f"视频生成失败: {data.get('message', '')}")
                await asyncio.sleep(5)
        raise TimeoutError("视频生成超时")

    async def _generate_siliconflow(self, config: ModelConfig, prompt: str, params: dict) -> str:
        """硅基流动视频生成"""
        api_base = config.api_base or "https://api.siliconflow.cn/v1"
        body: dict = {
            "model": config.model_name,
            "prompt": prompt,
            "image_url": params.get("image_url"),
        }
        if params.get("duration"):
            body["duration"] = params["duration"]
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{api_base}/videos/generations",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("video_url", data.get("url", ""))
