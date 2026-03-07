"""视频生成模型路由器 - 使用环境变量配置"""
import logging
import httpx
import asyncio

from core.config import settings

logger = logging.getLogger(__name__)


class VideoModelRouter:
    """视频生成模型路由器"""

    def __init__(self):
        """初始化视频生成服务"""
        self.provider = settings.video_gen_provider
        self.model = settings.video_gen_model
        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base

        # 验证 provider
        if self.provider != "volcengine":
            raise ValueError(f"Unsupported video generation provider: {self.provider}. Only 'volcengine' is supported.")

        # 验证必需配置
        if not self.api_key:
            raise ValueError("volcengine_api_key is required")
        if not self.model:
            raise ValueError("video_gen_model is required")

    async def generate_video(
        self,
        prompt: str,
        params: dict | None = None,
    ) -> str:
        """生成视频，返回视频URL"""
        params = params or {}

        # 构建请求体
        body: dict = {
            "model": self.model,
            "prompt": prompt,
        }

        # 添加可选参数
        if "image_url" in params:
            body["image_url"] = params["image_url"]
        if "duration" in params:
            body["duration"] = params["duration"]

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.api_base}/videos/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            # 火山引擎返回任务ID，需要轮询获取结果
            task_id = data.get("id", "")
            return await self._poll_video_result(task_id)

    async def _poll_video_result(self, task_id: str) -> str:
        """轮询火山引擎视频生成结果"""
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):  # 最多等待5分钟
                resp = await client.get(
                    f"{self.api_base}/async-result/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
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
