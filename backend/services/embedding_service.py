"""
Embedding 服务 - 文本向量化
"""
import logging
from typing import Any

import httpx

from core.config import settings
from core.http_client import get_http_client
from core.resilience import retry_async, with_timeout, with_fallback

logger = logging.getLogger(__name__)


class _ZhipuAIEmbeddings:
    """直接调用 ZhipuAI embedding API，绕过 LangChain 的 tiktoken 分词（ZhipuAI 只接受字符串）"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    @retry_async(max_attempts=3, base_delay=1.0, max_delay=10.0,
                 retriable_exceptions=(httpx.HTTPStatusError, httpx.ConnectError, TimeoutError),
                 service_name="ZhipuAI-Embedding")
    async def aembed_query(self, text: str) -> list[float]:
        client = get_http_client()
        resp = await client.post(
                self._base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
                timeout=30.0,
            )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            results.append(await self.aembed_query(text))
        return results


class _QwenEmbeddings:
    """直接调用 DashScope 原生 embedding API（text-embedding-v2 不支持 OpenAI 兼容格式）"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._base_url = (
            "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
            "text-embedding/text-embedding"
        )

    @retry_async(max_attempts=3, base_delay=1.0, max_delay=10.0,
                 retriable_exceptions=(httpx.HTTPStatusError, httpx.ConnectError, TimeoutError),
                 service_name="Qwen-Embedding")
    async def aembed_query(self, text: str) -> list[float]:
        client = get_http_client()
        resp = await client.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": {"texts": [text]},
                    "parameters": {"text_type": "query"},
                },
                timeout=30.0,
            )
        resp.raise_for_status()
        data = resp.json()
        return data["output"]["embeddings"][0]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        # DashScope 支持批量请求，但为简单起见逐条处理
        results = []
        for text in texts:
            results.append(await self.aembed_query(text))
        return results

class _VolcEngineEmbeddings:
    """直接调用火山引擎多模态 embedding API（doubao-embedding-vision 使用 /embeddings/multimodal 端点）"""

    def __init__(self, api_key: str, api_base: str, model: str):
        self.api_key = api_key
        self.model = model
        self._base_url = f"{api_base.rstrip('/')}/embeddings/multimodal"

    @retry_async(max_attempts=3, base_delay=1.0, max_delay=10.0,
                 retriable_exceptions=(httpx.HTTPStatusError, httpx.ConnectError, TimeoutError),
                 service_name="VolcEngine-Embedding")
    async def aembed_query(self, text: str) -> list[float]:
        client = get_http_client()
        resp = await client.post(
            self._base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "input": [{"type": "text", "text": text}],
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["data"]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            results.append(await self.aembed_query(text))
        return results


# 常见嵌入模型的向量维度
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "text-embedding-v3": 1536,       # Qwen
    "text-embedding-v2": 1536,       # Qwen
    "embedding-3": 2048,             # ZhipuAI
    "jina-embeddings-v3": 1024,
    "jina-embeddings-v2-base-zh": 768,
    "embed-multilingual-v3.0": 1024,  # Cohere
    "embed-english-v3.0": 1024,      # Cohere
}

# 支持 OpenAI 兼容接口的 provider（ZhipuAI / Qwen 单独处理，不走 LangChain OpenAIEmbeddings）
OPENAI_COMPATIBLE = {"openai", "siliconflow", "meta", "private"}

# Qwen text-embedding-v3 及以上版本支持兼容模式；v2 及以下需原生 API
# 这里列出支持 OpenAI 兼容格式的 Qwen embedding 模型
QWEN_OPENAI_COMPATIBLE_MODELS = {"text-embedding-v3"}

# 各 provider 的默认 base URL
PROVIDER_DEFAULT_BASE: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipuai": "https://open.bigmodel.cn/api/paas/v4",
    "siliconflow": "https://api.siliconflow.cn/v1",
}


class EmbeddingService:
    """Embedding 服务"""

    def __init__(self, tenant_id: str):
        """
        初始化 Embedding 服务，从环境变量读取配置

        Args:
            tenant_id: 租户 ID
        """
        self.tenant_id = tenant_id
        self.provider = settings.embedding_provider
        self.model = settings.embedding_model

        # 验证 provider（项目统一使用火山引擎）
        if self.provider != "volcengine":
            raise ValueError(f"Unsupported embedding provider: {self.provider}. Only 'volcengine' is supported.")

        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base
        self.dimension = settings.embedding_dimension

        # 验证必需配置
        if not self.api_key:
            raise ValueError("volcengine_api_key is required")
        if not self.model:
            raise ValueError("embedding_model is required")

        # 初始化 embedding 实例
        self.embeddings = self._init_volcengine_embeddings()

    def _init_volcengine_embeddings(self):
        """初始化火山引擎 embedding（直接调用 OpenAI 兼容 API，绕过 LangChain 的 tiktoken 分词）"""
        return _VolcEngineEmbeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model=self.model,
        )

    async def embed_text(self, text: str) -> list[float]:
        """
        将文本转换为向量（含超时保护）

        Args:
            text: 文本内容

        Returns:
            向量（浮点数列表）
        """
        try:
            vector = await with_timeout(
                self.embeddings.aembed_query(text),
                timeout=120.0,
                service_name="Embedding",
            )
            return vector
        except Exception as exc:
            logger.error("[Embedding] embed_text 失败 (tenant=%s): %s", self.tenant_id, exc)
            raise

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量向量化文本（含超时保护）

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            vectors = await with_timeout(
                self.embeddings.aembed_documents(texts),
                timeout=300.0,
                service_name="Embedding",
            )
            return vectors
        except Exception as exc:
            logger.error("[Embedding] embed_documents 失败 (tenant=%s, count=%d): %s",
                         self.tenant_id, len(texts), exc)
            raise

    async def get_dimension_from_model(self) -> int:
        """通过实际调用 embedding 模型获取向量维度"""
        vector = await self.embed_text("test")
        return len(vector)

    def get_dimension(self) -> int:
        """
        获取向量维度

        Returns:
            向量维度
        """
        return EMBEDDING_DIMENSIONS.get(self.model, self.dimension)

    def get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        return self.model

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息
        """
        return {
            "model": self.model,
            "dimension": self.get_dimension(),
            "provider": self.provider,
            "tenant_id": self.tenant_id,
        }
