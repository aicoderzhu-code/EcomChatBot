"""
知识库版本管理服务
"""
import logging
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ResourceNotFoundException
from models import KnowledgeBase
from models.knowledge_version import KnowledgeVersion

logger = logging.getLogger(__name__)


class KnowledgeVersionService:
    """知识库版本管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_snapshot(
        self,
        knowledge_id: str,
        change_type: str = "update",
        change_summary: str | None = None,
        changed_by: str | None = None,
    ) -> KnowledgeVersion:
        """在更新前保存当前版本快照"""
        # 获取当前知识条目
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

        version_id = f"kv_{uuid.uuid4().hex[:16]}"

        version = KnowledgeVersion(
            tenant_id=self.tenant_id,
            version_id=version_id,
            knowledge_id=knowledge_id,
            version_number=knowledge.version,
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            change_type=change_type,
            change_summary=change_summary,
            changed_by=changed_by,
        )

        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_version_history(
        self, knowledge_id: str, page: int = 1, size: int = 20,
    ) -> tuple[list[KnowledgeVersion], int]:
        """查询版本历史列表"""
        from sqlalchemy import func

        conditions = [
            KnowledgeVersion.tenant_id == self.tenant_id,
            KnowledgeVersion.knowledge_id == knowledge_id,
        ]

        count_stmt = select(func.count(KnowledgeVersion.id)).where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        stmt = (
            select(KnowledgeVersion)
            .where(and_(*conditions))
            .order_by(KnowledgeVersion.version_number.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        versions = result.scalars().all()

        return list(versions), total or 0

    async def get_version_detail(
        self, knowledge_id: str, version_number: int,
    ) -> KnowledgeVersion:
        """获取特定版本内容"""
        stmt = select(KnowledgeVersion).where(
            and_(
                KnowledgeVersion.tenant_id == self.tenant_id,
                KnowledgeVersion.knowledge_id == knowledge_id,
                KnowledgeVersion.version_number == version_number,
            )
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        if not version:
            raise ResourceNotFoundException("版本", f"{knowledge_id} v{version_number}")
        return version

    async def rollback_to_version(
        self, knowledge_id: str, version_number: int,
    ) -> KnowledgeBase:
        """回滚到指定版本"""
        # 获取目标版本
        target_version = await self.get_version_detail(knowledge_id, version_number)

        # 获取当前知识条目
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

        # 先保存当前版本快照
        await self.create_snapshot(
            knowledge_id,
            change_type="rollback",
            change_summary=f"回滚到版本 v{version_number}",
        )

        # 恢复到目标版本
        knowledge.title = target_version.title
        knowledge.content = target_version.content
        knowledge.category = target_version.category
        knowledge.version += 1

        await self.db.commit()
        await self.db.refresh(knowledge)

        return knowledge

    async def compare_versions(
        self, knowledge_id: str, v1: int, v2: int,
    ) -> dict:
        """对比两个版本的差异"""
        version1 = await self.get_version_detail(knowledge_id, v1)
        version2 = await self.get_version_detail(knowledge_id, v2)

        diff = {
            "knowledge_id": knowledge_id,
            "version_from": v1,
            "version_to": v2,
            "title_changed": version1.title != version2.title,
            "content_changed": version1.content != version2.content,
            "category_changed": version1.category != version2.category,
        }

        if diff["title_changed"]:
            diff["title_diff"] = {"old": version1.title, "new": version2.title}
        if diff["content_changed"]:
            diff["content_diff"] = {"old": version1.content, "new": version2.content}
        if diff["category_changed"]:
            diff["category_diff"] = {"old": version1.category, "new": version2.category}

        return diff
