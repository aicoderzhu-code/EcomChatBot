"""
RAG（检索增强生成）服务
集成 Milvus 向量数据库和 Embedding 模型
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.embedding_service import EmbeddingService
from services.knowledge_service import KnowledgeService
from services.milvus_service import MilvusService


class RAGService:
    """RAG 检索服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.knowledge_service = KnowledgeService(db, tenant_id)
        self.embedding_service = EmbeddingService(tenant_id)
        self.milvus_service = MilvusService(tenant_id)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        knowledge_type: str | None = None,
        use_vector_search: bool = True,
    ) -> list[dict]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            knowledge_type: 知识类型过滤
            use_vector_search: 是否使用向量搜索（否则使用关键词）
            
        Returns:
            检索结果列表
        """
        if use_vector_search:
            try:
                # 1. 将查询向量化
                query_vector = await self.embedding_service.embed_text(query)

                # 2. 在 Milvus 中搜索
                # 构建过滤表达式
                filter_expr = None
                if knowledge_type:
                    filter_expr = f"knowledge_type == '{knowledge_type}'"

                vector_results = await self.milvus_service.search_vectors(
                    query_vector=query_vector,
                    top_k=top_k,
                    filter_expr=filter_expr,
                )

                # 3. 从数据库获取完整信息
                knowledge_ids = [r["knowledge_id"] for r in vector_results]
                knowledge_items = await self.knowledge_service.get_knowledge_by_ids(
                    knowledge_ids
                )

                # 4. 合并结果
                results = []
                for vector_result in vector_results:
                    knowledge_id = vector_result["knowledge_id"]

                    # 找到对应的知识库项
                    knowledge_item = next(
                        (k for k in knowledge_items if k.knowledge_id == knowledge_id),
                        None,
                    )

                    if knowledge_item:
                        results.append(
                            {
                                "knowledge_id": knowledge_item.knowledge_id,
                                "title": knowledge_item.title,
                                "content": knowledge_item.content,
                                "score": vector_result["similarity"],
                                "category": knowledge_item.category,
                                "source": knowledge_item.source,
                                "tags": knowledge_item.tags,
                            }
                        )

                return results

            except Exception as e:
                print(f"向量搜索失败，回退到关键词搜索: {e}")
                # 回退到关键词搜索
                return await self._keyword_search(query, top_k, knowledge_type)

        else:
            # 使用关键词搜索
            return await self._keyword_search(query, top_k, knowledge_type)

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        knowledge_type: str | None = None,
    ) -> list[dict]:
        """
        关键词搜索（回退方案）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            knowledge_type: 知识类型过滤
            
        Returns:
            搜索结果列表
        """
        knowledge_list = await self.knowledge_service.search_knowledge(
            query=query,
            knowledge_type=knowledge_type,
            top_k=top_k,
        )

        results = []
        for knowledge in knowledge_list:
            results.append(
                {
                    "knowledge_id": knowledge.knowledge_id,
                    "title": knowledge.title,
                    "content": knowledge.content,
                    "score": 0.8,  # 关键词搜索使用固定分数
                    "category": knowledge.category,
                    "source": knowledge.source,
                    "tags": knowledge.tags,
                }
            )

        return results

    async def retrieve_and_generate(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        use_vector_search: bool = True,
    ) -> dict:
        """
        检索并生成回复（RAG 完整流程）
        
        Args:
            query: 查询文本
            conversation_history: 对话历史
            use_vector_search: 是否使用向量搜索
            
        Returns:
            生成结果
        """
        # 1. 检索相关知识
        retrieved_docs = await self.retrieve(
            query=query,
            top_k=3,
            use_vector_search=use_vector_search,
        )

        # 2. 构建上下文
        context = "\n\n".join(
            [
                f"[{doc['title']}]\n{doc['content']}\n（来源：{doc['source']}）"
                for doc in retrieved_docs
            ]
        )

        # 3. 使用对话链生成回复
        from services import ConversationChainService

        chain = ConversationChainService(
            db=self.db,
            tenant_id=self.tenant_id,
            conversation_id="rag-query",  # 临时会话 ID
        )

        result = await chain.chat_with_rag(
            user_input=query,
            knowledge_items=retrieved_docs,
        )

        return result

    async def index_knowledge(self, knowledge_id: str) -> dict[str, Any]:
        """
        为知识库项创建向量索引
        
        Args:
            knowledge_id: 知识库 ID
            
        Returns:
            索引结果
        """
        # 1. 获取知识库内容
        knowledge = await self.knowledge_service.get_knowledge(knowledge_id)

        # 2. 生成向量
        # 使用标题 + 内容
        text = f"{knowledge.title}\n{knowledge.content}"
        vector = await self.embedding_service.embed_text(text)

        # 3. 插入 Milvus
        import uuid

        vector_id = str(uuid.uuid4())

        await self.milvus_service.insert_vectors(
            knowledge_items=[
                {
                    "id": vector_id,
                    "knowledge_id": knowledge.knowledge_id,
                    "content": knowledge.content[:1000],  # 存储摘要
                }
            ],
            vectors=[vector],
        )

        return {
            "knowledge_id": knowledge_id,
            "vector_id": vector_id,
            "indexed": True,
        }

    async def index_batch_knowledge(
        self,
        knowledge_ids: list[str],
    ) -> dict[str, Any]:
        """
        批量索引知识库
        
        Args:
            knowledge_ids: 知识库 ID 列表
            
        Returns:
            批量索引结果
        """
        success_count = 0
        failed_count = 0
        errors = []

        for knowledge_id in knowledge_ids:
            try:
                await self.index_knowledge(knowledge_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"knowledge_id": knowledge_id, "error": str(e)})

        return {
            "total": len(knowledge_ids),
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
        }

    async def delete_knowledge_vectors(self, knowledge_ids: list[str]) -> int:
        """
        删除知识库向量
        
        Args:
            knowledge_ids: 知识库 ID 列表
            
        Returns:
            删除数量
        """
        count = await self.milvus_service.delete_vectors(knowledge_ids)
        return count

    def get_stats(self) -> dict[str, Any]:
        """
        获取 RAG 统计信息
        
        Returns:
            统计信息
        """
        milvus_stats = self.milvus_service.get_collection_stats()
        embedding_info = self.embedding_service.get_model_info()

        return {
            "tenant_id": self.tenant_id,
            "milvus": milvus_stats,
            "embedding": embedding_info,
        }
