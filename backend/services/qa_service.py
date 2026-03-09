"""
QA 对管理服务
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ResourceNotFoundException
from models.qa_pair import QAPair

logger = logging.getLogger(__name__)


class QAService:
    """QA 对管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_qa_pair(
        self,
        question: str,
        answer: str,
        category: str | None = None,
        priority: int = 0,
        knowledge_id: str | None = None,
    ) -> QAPair:
        """创建 QA 对并自动生成相似问变体"""
        qa_id = f"qa_{uuid.uuid4().hex[:16]}"

        qa_pair = QAPair(
            tenant_id=self.tenant_id,
            qa_id=qa_id,
            knowledge_id=knowledge_id,
            question=question,
            answer=answer,
            category=category,
            priority=priority,
            status="active",
        )

        # 自动生成相似问变体
        try:
            variations = await self.generate_variations(question)
            qa_pair.variations = variations
        except Exception as e:
            logger.warning("Failed to generate variations: %s", e)
            qa_pair.variations = []

        self.db.add(qa_pair)
        await self.db.commit()
        await self.db.refresh(qa_pair)

        return qa_pair

    async def get_qa_pair(self, qa_id: str) -> QAPair:
        """获取 QA 对"""
        stmt = select(QAPair).where(
            and_(
                QAPair.tenant_id == self.tenant_id,
                QAPair.qa_id == qa_id,
            )
        )
        result = await self.db.execute(stmt)
        qa_pair = result.scalar_one_or_none()
        if not qa_pair:
            raise ResourceNotFoundException("QA对", qa_id)
        return qa_pair

    async def list_qa_pairs(
        self,
        category: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[QAPair], int]:
        """查询 QA 对列表"""
        conditions = [
            QAPair.tenant_id == self.tenant_id,
        ]

        if category:
            conditions.append(QAPair.category == category)
        if status:
            conditions.append(QAPair.status == status)
        else:
            conditions.append(QAPair.status == "active")
        if keyword:
            conditions.append(
                or_(
                    QAPair.question.ilike(f"%{keyword}%"),
                    QAPair.answer.ilike(f"%{keyword}%"),
                )
            )

        count_stmt = select(func.count(QAPair.id)).where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        stmt = (
            select(QAPair)
            .where(and_(*conditions))
            .order_by(QAPair.priority.desc(), QAPair.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        qa_list = result.scalars().all()

        return list(qa_list), total or 0

    async def update_qa_pair(
        self,
        qa_id: str,
        question: str | None = None,
        answer: str | None = None,
        category: str | None = None,
        priority: int | None = None,
        variations: list[str] | None = None,
        status: str | None = None,
    ) -> QAPair:
        """更新 QA 对"""
        qa_pair = await self.get_qa_pair(qa_id)

        if question is not None:
            qa_pair.question = question
        if answer is not None:
            qa_pair.answer = answer
        if category is not None:
            qa_pair.category = category
        if priority is not None:
            qa_pair.priority = priority
        if variations is not None:
            qa_pair.variations = variations
        if status is not None:
            qa_pair.status = status

        await self.db.commit()
        await self.db.refresh(qa_pair)
        return qa_pair

    async def delete_qa_pair(self, qa_id: str) -> None:
        """删除 QA 对（软删除）"""
        qa_pair = await self.get_qa_pair(qa_id)
        qa_pair.status = "inactive"
        await self.db.commit()

    async def generate_variations(self, question: str) -> list[str]:
        """使用 LLM 生成问题变体"""
        from services.llm_service import LLMService

        prompt = f"""请为以下客服问题生成3-5个相似的问法变体。

原始问题：{question}

要求：
1. 保持语义相同，但用不同的表达方式
2. 包含口语化和正式的表达
3. 只返回变体列表，每行一个，不要编号

变体："""

        try:
            llm_service = LLMService()
            result = await llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个语言专家，擅长生成问题的多种表达方式。",
            )
            response_text = result.get("response", "") if isinstance(result, dict) else str(result)
            variations = [
                line.strip().lstrip("0123456789.-、）) ")
                for line in response_text.strip().split("\n")
                if line.strip() and len(line.strip()) > 2
            ]
            return variations[:5]
        except Exception as e:
            logger.error("Failed to generate variations: %s", e)
            return []

    async def import_from_list(
        self, items: list[dict],
    ) -> dict:
        """批量导入 QA 对"""
        results = {"success": [], "failed": []}
        for item in items:
            try:
                qa = await self.create_qa_pair(
                    question=item["question"],
                    answer=item["answer"],
                    category=item.get("category"),
                )
                results["success"].append(qa)
            except Exception as e:
                results["failed"].append({"item": item, "error": str(e)})
        return results

    async def get_popular_qa(
        self, category: str | None = None, limit: int = 10,
    ) -> list[QAPair]:
        """获取热门 QA 对（按使用次数排序）"""
        conditions = [
            QAPair.tenant_id == self.tenant_id,
            QAPair.status == "active",
        ]
        if category:
            conditions.append(QAPair.category == category)

        stmt = (
            select(QAPair)
            .where(and_(*conditions))
            .order_by(QAPair.use_count.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_use_count(self, qa_id: str) -> None:
        """增加使用次数"""
        qa_pair = await self.get_qa_pair(qa_id)
        qa_pair.use_count += 1
        await self.db.commit()
