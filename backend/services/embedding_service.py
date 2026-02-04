"""
Embedding 服务 - 文本向量化
"""
from typing import Any

from langchain_openai import OpenAIEmbeddings

from core.config import settings


class EmbeddingService:
    """Embedding 服务"""

    def __init__(self, tenant_id: str):
        """
        初始化 Embedding 服务
        
        Args:
            tenant_id: 租户 ID
        """
        self.tenant_id = tenant_id

        # 初始化 Embedding 模型
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

    def get_dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            向量维度
        """
        return settings.embedding_dimension

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息
        """
        return {
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension,
            "provider": "openai",
            "tenant_id": self.tenant_id,
        }
