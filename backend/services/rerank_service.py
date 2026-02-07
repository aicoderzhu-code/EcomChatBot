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
    COHERE = "cohere"
    JINA = "jina"
    BGE = "bge"
    CROSS_ENCODER = "cross_encoder"
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


class CohereRerankAdapter(RerankAdapter):
    """
    Cohere Rerank适配器

    使用Cohere的rerank-english-v3.0或rerank-multilingual-v3.0模型
    API文档: https://docs.cohere.com/reference/rerank
    """

    def __init__(
        self,
        api_key: str,
        model: str = "rerank-multilingual-v3.0"
    ):
        self._api_key = api_key
        self._default_model = model
        self._client = None

    def _get_client(self):
        """懒加载客户端"""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.AsyncClient(api_key=self._api_key)
            except ImportError:
                raise ImportError("请安装cohere包: pip install cohere")
        return self._client

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.COHERE

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用Cohere进行重排序"""
        if not documents:
            return []

        client = self._get_client()
        model = config.model or self._default_model

        try:
            response = await client.rerank(
                query=query,
                documents=documents,
                model=model,
                top_n=config.top_k,
                return_documents=True,
            )

            results = []
            for item in response.results:
                score = item.relevance_score
                if score >= config.min_score:
                    results.append(RerankResult(
                        document=documents[item.index],
                        score=score,
                        original_index=item.index,
                    ))

            return results

        except Exception as e:
            logger.error(f"Cohere rerank failed: {e}")
            raise


class JinaRerankAdapter(RerankAdapter):
    """
    Jina Rerank适配器

    使用Jina的reranker模型
    API文档: https://jina.ai/reranker/
    """

    BASE_URL = "https://api.jina.ai/v1/rerank"

    def __init__(
        self,
        api_key: str,
        model: str = "jina-reranker-v2-base-multilingual"
    ):
        self._api_key = api_key
        self._default_model = model

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.JINA

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用Jina进行重排序"""
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
                            document=item.get("document", {}).get("text", ""),
                            score=score,
                            original_index=item.get("index", 0),
                        ))

                return results

        except Exception as e:
            logger.error(f"Jina rerank failed: {e}")
            raise


class BGERerankAdapter(RerankAdapter):
    """
    BGE Rerank适配器

    使用本地BGE reranker模型
    模型: BAAI/bge-reranker-v2-m3
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                import torch

                self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name)
                self._model.eval()

                # 如果有GPU则使用
                if torch.cuda.is_available():
                    self._model = self._model.cuda()

            except ImportError:
                raise ImportError("请安装transformers和torch: pip install transformers torch")

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.BGE

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用BGE进行重排序"""
        if not documents:
            return []

        self._load_model()

        try:
            import torch

            # 构建查询-文档对
            pairs = [[query, doc] for doc in documents]

            # 在线程池中运行模型推理
            def compute_scores():
                with torch.no_grad():
                    inputs = self._tokenizer(
                        pairs,
                        padding=True,
                        truncation=True,
                        max_length=512,
                        return_tensors="pt"
                    )

                    if torch.cuda.is_available():
                        inputs = {k: v.cuda() for k, v in inputs.items()}

                    outputs = self._model(**inputs)
                    scores = outputs.logits.squeeze(-1).cpu().numpy()
                    return scores

            # 在事件循环中运行
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, compute_scores)

            # 构建结果
            results = []
            for idx, (doc, score) in enumerate(zip(documents, scores)):
                score_float = float(score)
                if score_float >= config.min_score:
                    results.append(RerankResult(
                        document=doc,
                        score=score_float,
                        original_index=idx,
                    ))

            # 按分数排序
            results.sort(key=lambda x: x.score, reverse=True)

            # 返回top_k
            return results[:config.top_k]

        except Exception as e:
            logger.error(f"BGE rerank failed: {e}")
            raise


class CrossEncoderRerankAdapter(RerankAdapter):
    """
    Cross-Encoder Rerank适配器

    使用sentence-transformers的CrossEncoder模型
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self._model_name)
            except ImportError:
                raise ImportError("请安装sentence-transformers: pip install sentence-transformers")

    @property
    def provider(self) -> RerankProvider:
        return RerankProvider.CROSS_ENCODER

    async def rerank(
        self,
        query: str,
        documents: List[str],
        config: RerankConfig
    ) -> List[RerankResult]:
        """使用CrossEncoder进行重排序"""
        if not documents:
            return []

        self._load_model()

        try:
            # 构建查询-文档对
            pairs = [(query, doc) for doc in documents]

            # 在线程池中运行模型推理
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                self._model.predict,
                pairs
            )

            # 构建结果
            results = []
            for idx, (doc, score) in enumerate(zip(documents, scores)):
                score_float = float(score)
                if score_float >= config.min_score:
                    results.append(RerankResult(
                        document=doc,
                        score=score_float,
                        original_index=idx,
                    ))

            # 按分数排序
            results.sort(key=lambda x: x.score, reverse=True)

            # 返回top_k
            return results[:config.top_k]

        except Exception as e:
            logger.error(f"CrossEncoder rerank failed: {e}")
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
    cohere_api_key: Optional[str] = None,
    jina_api_key: Optional[str] = None,
    use_local_bge: bool = False,
    use_cross_encoder: bool = False,
    llm_service: Optional[Any] = None,
) -> RerankService:
    """
    初始化重排序服务

    Args:
        cohere_api_key: Cohere API密钥
        jina_api_key: Jina API密钥
        use_local_bge: 是否使用本地BGE模型
        use_cross_encoder: 是否使用CrossEncoder
        llm_service: LLM服务实例（用于LLM重排序）

    Returns:
        RerankService实例
    """
    service = get_rerank_service()

    if cohere_api_key:
        try:
            adapter = CohereRerankAdapter(api_key=cohere_api_key)
            service.register_adapter(adapter, is_default=True)
        except Exception as e:
            logger.warning(f"Failed to initialize Cohere rerank: {e}")

    if jina_api_key:
        try:
            adapter = JinaRerankAdapter(api_key=jina_api_key)
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize Jina rerank: {e}")

    if use_local_bge:
        try:
            adapter = BGERerankAdapter()
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize BGE rerank: {e}")

    if use_cross_encoder:
        try:
            adapter = CrossEncoderRerankAdapter()
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize CrossEncoder rerank: {e}")

    if llm_service:
        try:
            adapter = LLMRerankAdapter(llm_service=llm_service)
            service.register_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM rerank: {e}")

    logger.info(f"Rerank service initialized with providers: {service.get_available_providers()}")
    return service
