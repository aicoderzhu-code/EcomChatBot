"""
Rerank重排序服务

用于RAG检索结果的重新排序，提高相关性
支持多种重排序模型和策略
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RerankProvider(str, Enum):
    """重排序提供商"""
    QWEN = "qwen"
    SILICONFLOW = "siliconflow"
    LLM = "llm"  # 使用LLM进行重排序


@dataclass
class RerankResult:
    """重排序结果"""
    document: str
    score: float
    original_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankConfig:
    """重排序配置"""
    top_k: int = 10  # 返回前K个结果
    min_score: float = 0.0  # 最低分数阈值
    model: Optional[str] = None
    return_scores: bool = True


class RerankAdapter(ABC):
    """重排序适配器基类"""

    @property
    @abstractmethod
    def provider(self) -> RerankProvider:
        """提供商标识"""
        pass

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """
        重排序文档

        Args:
            query: 查询文本
            documents: 待排序的文档列表
            config: 重排序配置

        Returns:
            排序后的结果列表
        """
        pass


class QwenRerankAdapter(RerankAdapter):
    """
    通义千问 Rerank 适配器

    调用 DashScope rerank API（gte-rerank 等模型）
    """

    BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

    def __init__(
        self,
        api_key: str,
        model: str = "gte-rerank"
    ):
        self._api_key = api_key
        self._default_model = model

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.QWEN

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用通义千问进行重排序"""
        if not documents:
            return []

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.model or self._default_model,
                        "input": {"query": query, "documents": documents},
                        "parameters": {
                            "top_n": config.top_k,
                            "return_documents": False,
                        },
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("output", {}).get("results", []):
                    score = item.get("relevance_score", 0)
                    if score >= config.min_score:
                        results.append(RerankResult(
                            document=documents[item["index"]],
                            score=score,
                            original_index=item["index"],
                        ))

                return results

        except Exception as e:
            logger.error(f"Qwen rerank failed: {e}")
            raise


class SiliconFlowRerankAdapter(RerankAdapter):
    """
    SiliconFlow Rerank 适配器

    调用 SiliconFlow rerank API（OpenAI 兼容格式）
    """

    BASE_URL = "https://api.siliconflow.cn/v1/rerank"

    def __init__(
        self,
        api_key: str,
        model: str = "BAAI/bge-reranker-v2-m3"
    ):
        self._api_key = api_key
        self._default_model = model

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.SILICONFLOW

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用 SiliconFlow 进行重排序"""
        if not documents:
            return []

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.model or self._default_model,
                        "query": query,
                        "documents": documents,
                        "top_n": config.top_k,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    score = item.get("relevance_score", 0)
                    if score >= config.min_score:
                        results.append(RerankResult(
                            document=documents[item["index"]],
                            score=score,
                            original_index=item["index"],
                        ))

                return results

        except Exception as e:
            logger.error(f"SiliconFlow rerank failed: {e}")
            raise


class LLMRerankAdapter(RerankAdapter):
    """
    LLM Rerank适配器

    使用LLM进行重排序，适合小批量高精度场景
    """

    def __init__(self, llm_service):
        """
        初始化LLM重排序适配器

        Args:
            llm_service: LLM服务实例
        """
        self._llm_service = llm_service

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.LLM

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用LLM进行重排序"""
        if not documents:
            return []

        # 构建提示词
        docs_text = ""
        for i, doc in enumerate(documents):
            docs_text += f"[{i}] {doc[:500]}\n\n"  # 截断过长的文档

        prompt = f"""请根据查询语句对以下文档进行相关性评分。

查询: {query}

文档列表:
{docs_text}

请为每个文档评分（0-10分，10分最相关）。
只输出JSON格式结果，格式为: {{"scores": [分数1, 分数2, ...]}}"""

        try:
            # 调用LLM
            response = await self._llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
            )

            # 解析结果
            import json
            import re

            content = response.get("content", "")
            # 提取JSON
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                scores = data.get("scores", [])

                # 构建结果
                results = []
                for idx, (doc, score) in enumerate(zip(documents, scores)):
                    score_normalized = float(score) / 10.0  # 归一化到0-1
                    if score_normalized >= config.min_score:
                        results.append(RerankResult(
                            document=doc,
                            score=score_normalized,
                            original_index=idx,
                        ))

                # 按分数排序
                results.sort(key=lambda x: x.score, reverse=True)
                return results[:config.top_k]

            # 解析失败，返回原顺序
            logger.warning("Failed to parse LLM rerank response")
            return [
                RerankResult(document=doc, score=1.0 - i * 0.1, original_index=i)
                for i, doc in enumerate(documents[:config.top_k])
            ]

        except Exception as e:
            logger.error(f"LLM rerank failed: {e}")
            raise


class RerankService:
    """
    重排序服务

    统一的重排序接口，支持多种后端
    """

    def __init__(self):
        self._adapters: Dict[RerankProvider, RerankAdapter] = {}
        self._default_provider: Optional[RerankProvider] = None

    def register_adapter(
        self,
        adapter: RerankAdapter,
        is_default: bool = False
    ):
        """注册重排序适配器"""
        self._adapters[adapter.provider] = adapter
        if is_default or self._default_provider is None:
            self._default_provider = adapter.provider
        logger.info(f"Registered rerank adapter: {adapter.provider.value}")

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10,
        min_score: float = 0.0,
        provider: Optional[RerankProvider] = None,
        model: Optional[str] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[RerankResult]:
        """
        重排序文档

        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前K个结果
            min_score: 最低分数阈值
            provider: 使用的提供商（可选）
            model: 使用的模型（可选）
            metadata_list: 文档元数据列表（可选）

        Returns:
            排序后的结果列表
        """
        if not documents:
            return []

        # 选择适配器
        provider = provider or self._default_provider
        if provider not in self._adapters:
            raise ValueError(f"Rerank provider {provider} not registered")

        adapter = self._adapters[provider]
        config = RerankConfig(
            top_k=top_k,
            min_score=min_score,
            model=model,
        )

        # 执行重排序
        results = await adapter.rerank(query, documents, config)

        # 附加元数据
        if metadata_list:
            for result in results:
                if result.original_index < len(metadata_list):
                    result.metadata = metadata_list[result.original_index]

        return results

    async def rerank_with_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        content_key: str = "content",
        top_k: int = 10,
        min_score: float = 0.0,
        provider: Optional[RerankProvider] = None,
    ) -> List[Dict[str, Any]]:
        """
        重排序带元数据的文档块

        这是一个便捷方法，用于处理RAG检索结果

        Args:
            query: 查询文本
            chunks: 文档块列表，每个块是一个字典
            content_key: 内容字段的键名
            top_k: 返回前K个结果
            min_score: 最低分数阈值
            provider: 使用的提供商

        Returns:
            排序后的文档块列表，每个块增加rerank_score字段
        """
        if not chunks:
            return []

        # 提取文档内容
        documents = [chunk.get(content_key, "") for chunk in chunks]

        # 执行重排序
        results = await self.rerank(
            query=query,
            documents=documents,
            top_k=top_k,
            min_score=min_score,
            provider=provider,
        )

        # 构建输出
        output = []
        for result in results:
            original_chunk = chunks[result.original_index].copy()
            original_chunk["rerank_score"] = result.score
            output.append(original_chunk)

        return output

    def get_available_providers(self) -> List[RerankProvider]:
        """获取所有可用的提供商"""
        return list(self._adapters.keys())


# 全局服务实例
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """获取全局重排序服务实例"""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service


async def init_rerank_service(
    qwen_api_key: Optional[str] = None,
    siliconflow_api_key: Optional[str] = None,
    llm_service: Optional[Any] = None,
) -> RerankService:
    """
    初始化重排序服务

    Args:
        qwen_api_key: 通义千问 API密钥
        siliconflow_api_key: SiliconFlow API密钥
        llm_service: LLM服务实例（用于LLM重排序）

    Returns:
        RerankService实例
    """
    service = get_rerank_service()

    if qwen_api_key:
        try:
            adapter = QwenRerankAdapter(api_key=qwen_api_key)
            service.register_adapter(adapter, is_default=True)
        except Exception as e:
            logger.warning(f"Failed to initialize Qwen rerank: {e}")

    if siliconflow_api_key:
        try:
            adapter = SiliconFlowRerankAdapter(api_key=siliconflow_api_key)
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize SiliconFlow rerank: {e}")

    if llm_service:
        try:
            adapter = LLMRerankAdapter(llm_service=llm_service)
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM rerank: {e}")

    logger.info(f"Rerank service initialized with providers: {service.get_available_providers()}")
    return service
