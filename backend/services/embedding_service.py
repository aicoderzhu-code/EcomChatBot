"""
Embedding 服务 - 文本向量化
"""
from typing import Any

import httpx
from langchain_openai import OpenAIEmbeddings

from core.config import settings


class _ZhipuAIEmbeddings:
    """直接调用 ZhipuAI embedding API，绕过 LangChain 的 tiktoken 分词（ZhipuAI 只接受字符串）"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    async def aembed_query(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
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

    async def aembed_query(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    def __init__(self, tenant_id: str, model_config=None):
        """
        初始化 Embedding 服务

        Args:
            tenant_id: 租户 ID
            model_config: 可选的 ModelConfig ORM 对象；若提供则优先使用，否则回退到全局配置
        """
        self.tenant_id = tenant_id
        self._model_config = model_config

        if model_config and model_config.provider == "zhipuai":
            # ZhipuAI 不兼容 LangChain 的 tiktoken 分词，直接用 httpx 调用
            self.embeddings = _ZhipuAIEmbeddings(
                api_key=model_config.api_key,
                model=model_config.model_name,
            )
        elif model_config and model_config.provider == "qwen":
            # Qwen: v3 支持 OpenAI 兼容格式，v2 及以下需要 DashScope 原生 API
            if model_config.model_name in QWEN_OPENAI_COMPATIBLE_MODELS:
                base = model_config.api_base or PROVIDER_DEFAULT_BASE["qwen"]
                self.embeddings = OpenAIEmbeddings(
                    model=model_config.model_name,
                    openai_api_key=model_config.api_key,
                    openai_api_base=base,
                )
            else:
                # text-embedding-v2 等需要 DashScope 原生 API
                self.embeddings = _QwenEmbeddings(
                    api_key=model_config.api_key,
                    model=model_config.model_name,
                )
        elif model_config and model_config.provider in OPENAI_COMPATIBLE:
            base = model_config.api_base or PROVIDER_DEFAULT_BASE.get(
                model_config.provider, "https://api.openai.com/v1"
            )
            self.embeddings = OpenAIEmbeddings(
                model=model_config.model_name,
                openai_api_key=model_config.api_key,
                openai_api_base=base,
            )
        else:
            # 回退到全局配置（兼容原有行为）
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key=settings.openai_api_key,
                openai_api_base=settings.openai_api_base,
            )

    async def embed_text(self, text: str) -> list[float]:
        """
        将文本转换为向量

        Args:
            text: 文本内容

        Returns:
            向量（浮点数列表）
        """
        vector = await self.embeddings.aembed_query(text)
        return vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        vectors = await self.embeddings.aembed_documents(texts)
        return vectors

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
        if self._model_config:
            return EMBEDDING_DIMENSIONS.get(self._model_config.model_name, 1536)
        return settings.embedding_dimension

    def get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        if self._model_config:
            return self._model_config.model_name
        return settings.embedding_model

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息
        """
        if self._model_config:
            return {
                "model": self._model_config.model_name,
                "dimension": self.get_dimension(),
                "provider": self._model_config.provider,
                "tenant_id": self.tenant_id,
            }
        return {
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension,
            "provider": "openai",
            "tenant_id": self.tenant_id,
        }
