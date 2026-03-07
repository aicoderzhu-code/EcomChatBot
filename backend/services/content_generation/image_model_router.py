"""图像生成模型路由器 - 使用环境变量配置"""
import logging
import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class ImageModelRouter:
    """图像生成模型路由器"""

    def __init__(self):
        """初始化图片生成服务"""
        self.provider = settings.image_gen_provider
        self.model = settings.image_gen_model
        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base

        # 验证 provider
        if self.provider != "volcengine":
            raise ValueError(f"Unsupported image generation provider: {self.provider}. Only 'volcengine' is supported.")

        # 验证必需配置
        if not self.api_key:
            raise ValueError("volcengine_api_key is required")
        if not self.model:
            raise ValueError("image_gen_model is required")

    async def generate_image(
        self,
        prompt: str,
        params: dict | None = None,
    ) -> list[str]:
        """生成图像，返回图像URL列表"""
        params = params or {}

        # 构建请求体
        body: dict = {
            "model": self.model,
            "prompt": prompt,
        }

        # 添加可选参数
        if "size" in params:
            body["size"] = params["size"]
        if "n" in params:
            body["n"] = params["n"]

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.api_base}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            # 解析响应
            return [item["url"] for item in data.get("data", [])]
