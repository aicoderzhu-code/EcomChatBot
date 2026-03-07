"""图像生成模型路由器 - 使用环境变量配置"""
import logging
import asyncio
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

        # 火山引擎图片生成使用 OpenAI 兼容的接口
        body: dict = {
            "model": self.model,
            "prompt": prompt,
        }

        # 处理尺寸参数
        # 火山引擎要求图片至少 3686400 像素（约 1920x1920）
        if "size" in params:
            size_str = params["size"]
            try:
                # 解析尺寸字符串 "WxH"
                width, height = map(int, size_str.split("x"))
                total_pixels = width * height

                # 如果尺寸太小，使用默认尺寸 2048x2048
                if total_pixels < 3686400:
                    logger.warning(f"Requested size {size_str} is too small (min 3686400 pixels), using 2048x2048")
                    body["size"] = "2048x2048"
                else:
                    body["size"] = size_str
            except (ValueError, AttributeError):
                # 如果解析失败，使用默认尺寸
                logger.warning(f"Invalid size format: {size_str}, using 2048x2048")
                body["size"] = "2048x2048"
        else:
            # 没有指定尺寸，使用默认值
            body["size"] = "2048x2048"

        # 生成数量
        if "n" in params:
            body["n"] = params["n"]
        else:
            body["n"] = 1  # 默认生成 1 张图片

        async with httpx.AsyncClient(timeout=180) as client:
            # 火山引擎图片生成 API
            resp = await client.post(
                f"{self.api_base}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )

            # 记录响应以便调试
            logger.info(f"Image generation response status: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"Image generation failed: {resp.text}")

            resp.raise_for_status()
            data = resp.json()

            # 解析响应 - OpenAI 格式
            urls = []
            if "data" in data:
                for item in data["data"]:
                    if "url" in item:
                        urls.append(item["url"])

            if not urls:
                raise ValueError("No image URLs in response")

            return urls
