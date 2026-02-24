"""
知识库管理服务
"""
import asyncio
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppException, ResourceNotFoundException
from core.security import generate_tenant_id
from models import KnowledgeBase
from models.knowledge_settings import KnowledgeSettings


async def _embed_in_background(knowledge_id: str, tenant_id: str, embedding_model_id: int) -> None:
    """后台向量化任务，使用独立的 DB session，不阻塞 HTTP 响应"""
    from db.session import AsyncSessionLocal
    from models.model_config import ModelConfig
    from services.rag_service import RAGService

    # 先标记为"执行中"
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(KnowledgeBase)
                .where(KnowledgeBase.knowledge_id == knowledge_id)
                .values(embedding_status="processing")
            )
            await db.commit()
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ModelConfig).where(ModelConfig.id == embedding_model_id)
            result = await db.execute(stmt)
            model_config = result.scalar_one_or_none()
            if model_config:
                rag = RAGService(db, tenant_id, embedding_model_config=model_config)
                await rag.index_knowledge(knowledge_id)
            await db.execute(
                sa_update(KnowledgeBase)
                .where(KnowledgeBase.knowledge_id == knowledge_id)
                .values(embedding_status="completed")
            )
            await db.commit()
    except Exception as e:
        import traceback
        print(f"[Background Embedding] 向量化失败 knowledge_id={knowledge_id}: {e}")
        print(f"[Background Embedding] 完整错误:\n{traceback.format_exc()}")
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_update(KnowledgeBase)
                    .where(KnowledgeBase.knowledge_id == knowledge_id)
                    .values(embedding_status="failed")
                )
                await db.commit()
        except Exception:
            pass


class KnowledgeService:
    """知识库管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_knowledge(
        self,
        knowledge_type: str,
        title: str,
        content: str,
        category: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
        priority: int = 0,
        chunk_count: int = 1,
    ) -> KnowledgeBase:
        """创建知识条目"""
        import uuid
        timestamp = int(datetime.utcnow().timestamp())
        random_suffix = uuid.uuid4().hex[:8]
        knowledge_id = f"kb_{self.tenant_id}_{timestamp}_{random_suffix}"

        # 提前查询 embedding 配置，决定初始状态
        ks = await self.get_settings()
        initial_embedding_status = "pending" if ks.embedding_model_id else "completed"

        knowledge = KnowledgeBase(
            tenant_id=self.tenant_id,
            knowledge_id=knowledge_id,
            knowledge_type=knowledge_type,
            title=title,
            content=content,
            category=category,
            tags=tags,
            source=source,
            priority=priority,
            status="active",
            embedding_status=initial_embedding_status,
            chunk_count=chunk_count,
        )

        self.db.add(knowledge)
        await self.db.commit()
        await self.db.refresh(knowledge)

        # 触发向量化（如已配置 embedding 模型）—— 后台异步执行，不阻塞 HTTP 响应
        if ks.embedding_model_id:
            asyncio.create_task(
                _embed_in_background(knowledge.knowledge_id, self.tenant_id, ks.embedding_model_id)
            )

        return knowledge

    async def _trigger_embedding(self, knowledge: KnowledgeBase, embedding_model_id: int) -> None:
        """触发单条知识的向量化"""
        from models.model_config import ModelConfig
        from services.rag_service import RAGService

        model_stmt = select(ModelConfig).where(ModelConfig.id == embedding_model_id)
        result = await self.db.execute(model_stmt)
        model_config = result.scalar_one_or_none()
        if model_config:
            rag = RAGService(self.db, self.tenant_id, embedding_model_config=model_config)
            await rag.index_knowledge(knowledge.knowledge_id)

    async def get_settings(self) -> KnowledgeSettings:
        """获取或自动创建租户知识库设置"""
        stmt = select(KnowledgeSettings).where(KnowledgeSettings.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        s = result.scalar_one_or_none()
        if not s:
            s = KnowledgeSettings(tenant_id=self.tenant_id)
            self.db.add(s)
            await self.db.commit()
            await self.db.refresh(s)
        return s

    async def update_settings(
        self,
        embedding_model_id: int | None,
        rerank_model_id: int | None,
    ) -> KnowledgeSettings:
        """更新设置；若更改 embedding_model_id 则先检查是否有向量化文档"""
        s = await self.get_settings()
        if embedding_model_id != s.embedding_model_id:
            if await self.has_indexed_documents():
                raise AppException("知识库已有文档，无法更换嵌入模型。请先删除所有文档。")
        s.embedding_model_id = embedding_model_id
        s.rerank_model_id = rerank_model_id
        s.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def get_stats(self) -> tuple[int, int]:
        """返回 (总文档数, 总切片数)"""
        stmt = select(
            func.count(KnowledgeBase.id),
            func.coalesce(func.sum(KnowledgeBase.chunk_count), 0),
        ).where(
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.status == "active",
        )
        row = (await self.db.execute(stmt)).one()
        return int(row[0]), int(row[1])

    async def has_indexed_documents(self) -> bool:
        """是否有已成功向量化的文档（仅完成向量化的文档才锁定嵌入模型切换）"""
        stmt = select(func.count(KnowledgeBase.id)).where(
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.status == "active",
            KnowledgeBase.embedding_status == "completed",
        )
        count = await self.db.scalar(stmt)
        return (count or 0) > 0

    async def get_knowledge_by_ids(
        self,
        knowledge_ids: list[str],
    ) -> list[KnowledgeBase]:
        """
        批量获取知识库项

        Args:
            knowledge_ids: 知识库 ID 列表

        Returns:
            知识库项列表
        """
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.knowledge_id.in_(knowledge_ids),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_knowledge(self, knowledge_id: str) -> KnowledgeBase:
        """获取知识条目"""
        stmt = select(KnowledgeBase).where(
            and_(
                KnowledgeBase.tenant_id == self.tenant_id,
                KnowledgeBase.knowledge_id == knowledge_id,
            )
        )
        result = await self.db.execute(stmt)
        knowledge = result.scalar_one_or_none()

        if not knowledge:
            raise ResourceNotFoundException("知识", knowledge_id)

        return knowledge

    async def list_knowledge(
        self,
        knowledge_type: str | None = None,
        category: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[KnowledgeBase], int]:
        """查询知识列表"""
        conditions = [
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.status == "active",
        ]

        if knowledge_type:
            conditions.append(KnowledgeBase.knowledge_type == knowledge_type)
        if category:
            conditions.append(KnowledgeBase.category == category)
        if keyword:
            conditions.append(
                or_(
                    KnowledgeBase.title.ilike(f"%{keyword}%"),
                    KnowledgeBase.content.ilike(f"%{keyword}%"),
                )
            )

        # 查询总数
        count_stmt = select(func.count(KnowledgeBase.id)).where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        # 分页查询
        stmt = (
            select(KnowledgeBase)
            .where(and_(*conditions))
            .order_by(KnowledgeBase.priority.desc(), KnowledgeBase.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.db.execute(stmt)
        knowledge_list = result.scalars().all()

        return list(knowledge_list), total or 0

    async def update_knowledge(
        self,
        knowledge_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        priority: int | None = None,
    ) -> KnowledgeBase:
        """更新知识条目"""
        knowledge = await self.get_knowledge(knowledge_id)

        if title is not None:
            knowledge.title = title
        if content is not None:
            knowledge.content = content
        if category is not None:
            knowledge.category = category
        if tags is not None:
            knowledge.tags = tags
        if priority is not None:
            knowledge.priority = priority

        knowledge.version += 1

        await self.db.commit()
        await self.db.refresh(knowledge)

        # TODO: 更新向量
        # if title or content:
        #     await self.update_embedding(knowledge)

        return knowledge

    async def delete_knowledge(self, knowledge_id: str) -> None:
        """删除知识条目（软删除）"""
        knowledge = await self.get_knowledge(knowledge_id)
        knowledge.status = "inactive"
        await self.db.commit()

        # TODO: 从 Milvus 删除向量
        # await self.delete_embedding(knowledge)

    async def search_knowledge(
        self,
        query: str,
        knowledge_type: str | None = None,
        top_k: int = 5,
    ) -> list[KnowledgeBase]:
        """
        搜索知识（简单关键词搜索）

        TODO: 使用 RAG 向量搜索替代
        """
        conditions = [
            KnowledgeBase.tenant_id == self.tenant_id,
            KnowledgeBase.status == "active",
        ]

        if knowledge_type:
            conditions.append(KnowledgeBase.knowledge_type == knowledge_type)

        # 简单的文本搜索
        conditions.append(
            or_(
                KnowledgeBase.title.ilike(f"%{query}%"),
                KnowledgeBase.content.ilike(f"%{query}%"),
            )
        )

        stmt = (
            select(KnowledgeBase)
            .where(and_(*conditions))
            .order_by(KnowledgeBase.priority.desc())
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_use_count(self, knowledge_id: str) -> None:
        """增加使用次数"""
        knowledge = await self.get_knowledge(knowledge_id)
        knowledge.use_count += 1
        knowledge.last_used_at = datetime.utcnow()
        await self.db.commit()

    async def batch_import(
        self,
        knowledge_items: list[dict],
    ) -> dict:
        """批量导入知识，返回 {created: [{knowledge_id, ...}], failed: [...]}"""
        results = {"success": [], "failed": []}

        for item in knowledge_items:
            try:
                knowledge = await self.create_knowledge(
                    knowledge_type=item.get("knowledge_type", "faq"),
                    title=item["title"],
                    content=item["content"],
                    category=item.get("category"),
                    tags=item.get("tags"),
                    source=item.get("source"),
                    priority=item.get("priority", 0),
                )
                results["success"].append(knowledge)
            except Exception as e:
                results["failed"].append({"item": item, "error": str(e)})

        return results
