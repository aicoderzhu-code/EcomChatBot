"""
自动知识提取服务
从历史对话中提取高频 QA
"""
import json
import logging
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ResourceNotFoundException
from models import Conversation, Message
from models.knowledge_candidate import KnowledgeCandidate

logger = logging.getLogger(__name__)


class KnowledgeExtractionService:
    """自动知识提取服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def extract_from_conversation(
        self, conversation_id: str,
    ) -> list[KnowledgeCandidate]:
        """从对话中提取候选知识"""
        # 获取对话消息
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.tenant_id == self.tenant_id,
                    Message.conversation_id == conversation_id,
                    Message.role.in_(["user", "assistant"]),
                )
            )
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())

        if len(messages) < 4:
            return []

        # 构建对话文本
        conversation_text = self._format_conversation(messages)

        # 调用 LLM 提取 QA 对
        qa_pairs = await self._extract_qa_with_llm(conversation_text)

        # 创建候选知识记录
        candidates = []
        for qa in qa_pairs:
            candidate_id = f"kc_{uuid.uuid4().hex[:16]}"
            candidate = KnowledgeCandidate(
                tenant_id=self.tenant_id,
                candidate_id=candidate_id,
                conversation_id=conversation_id,
                question=qa["question"],
                answer=qa["answer"],
                category=qa.get("category"),
                confidence_score=qa.get("confidence", 0.7),
                status="pending",
            )
            self.db.add(candidate)
            candidates.append(candidate)

        if candidates:
            await self.db.commit()
            for c in candidates:
                await self.db.refresh(c)

        return candidates

    def _format_conversation(self, messages: list[Message]) -> str:
        """格式化对话"""
        lines = []
        for msg in messages:
            role = "用户" if msg.role == "user" else "客服"
            lines.append(f"{role}：{msg.content}")
        return "\n".join(lines)

    async def _extract_qa_with_llm(self, conversation_text: str) -> list[dict]:
        """使用 LLM 提取 QA 对"""
        from services.llm_service import LLMService

        prompt = f"""请从以下客服对话中提取可以入库的问答对。

## 要求
1. 提取用户的核心问题和客服的解决方案
2. 问题应具有通用性（其他用户也可能问到）
3. 答案应完整、准确
4. 为每对 QA 评估置信度（0-1，越高表示越适合入库）
5. 推荐一个分类标签

## 对话内容
{conversation_text}

## 输出格式
请以 JSON 数组格式输出，每个元素包含：
- question: 提取的问题
- answer: 提取的答案
- category: 推荐分类
- confidence: 置信度（0-1）

只输出 JSON 数组，不要包含其他内容。如果没有适合提取的 QA 对，输出空数组 []。

JSON:"""

        try:
            llm_service = LLMService()
            result = await llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个知识库管理专家，擅长从对话中提取高质量的问答对。只输出JSON格式。",
            )
            response_text = result.get("response", "") if isinstance(result, dict) else str(result)

            # 解析 JSON
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                response_text = response_text.rsplit("```", 1)[0]

            qa_pairs = json.loads(response_text)
            if not isinstance(qa_pairs, list):
                return []
            return qa_pairs
        except Exception as e:
            logger.error("Failed to extract QA from conversation: %s", e)
            return []

    async def approve_candidate(
        self, candidate_id: str, approved_by: str | None = None,
        question: str | None = None, answer: str | None = None,
        category: str | None = None,
    ) -> KnowledgeCandidate:
        """审核通过候选知识 -> 创建 QA 对"""
        candidate = await self._get_candidate(candidate_id)

        if candidate.status != "pending":
            from core.exceptions import AppException
            raise AppException(f"候选知识状态为 {candidate.status}，无法审核")

        # 创建 QA 对
        from services.qa_service import QAService
        qa_service = QAService(self.db, self.tenant_id)
        qa_pair = await qa_service.create_qa_pair(
            question=question or candidate.question,
            answer=answer or candidate.answer,
            category=category or candidate.category,
        )

        # 更新候选知识状态
        candidate.status = "approved"
        candidate.approved_by = approved_by
        candidate.created_knowledge_id = qa_pair.qa_id

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def reject_candidate(
        self, candidate_id: str, reason: str,
    ) -> KnowledgeCandidate:
        """拒绝候选知识"""
        candidate = await self._get_candidate(candidate_id)

        if candidate.status != "pending":
            from core.exceptions import AppException
            raise AppException(f"候选知识状态为 {candidate.status}，无法拒绝")

        candidate.status = "rejected"
        candidate.rejection_reason = reason

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def batch_approve(
        self, candidate_ids: list[str], approved_by: str | None = None,
    ) -> dict:
        """批量审核通过"""
        results = {"success": [], "failed": []}
        for cid in candidate_ids:
            try:
                await self.approve_candidate(cid, approved_by=approved_by)
                results["success"].append(cid)
            except Exception as e:
                results["failed"].append({"candidate_id": cid, "error": str(e)})
        return results

    async def list_candidates(
        self, status: str | None = None, page: int = 1, size: int = 20,
    ) -> tuple[list[KnowledgeCandidate], int]:
        """查询候选知识列表"""
        conditions = [KnowledgeCandidate.tenant_id == self.tenant_id]
        if status:
            conditions.append(KnowledgeCandidate.status == status)

        count_stmt = select(func.count(KnowledgeCandidate.id)).where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        stmt = (
            select(KnowledgeCandidate)
            .where(and_(*conditions))
            .order_by(KnowledgeCandidate.confidence_score.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        return list(candidates), total or 0

    async def get_metrics(self) -> dict:
        """获取提取统计"""
        total_stmt = select(func.count(KnowledgeCandidate.id)).where(
            KnowledgeCandidate.tenant_id == self.tenant_id
        )
        total = await self.db.scalar(total_stmt) or 0

        approved_stmt = select(func.count(KnowledgeCandidate.id)).where(
            and_(
                KnowledgeCandidate.tenant_id == self.tenant_id,
                KnowledgeCandidate.status == "approved",
            )
        )
        approved = await self.db.scalar(approved_stmt) or 0

        rejected_stmt = select(func.count(KnowledgeCandidate.id)).where(
            and_(
                KnowledgeCandidate.tenant_id == self.tenant_id,
                KnowledgeCandidate.status == "rejected",
            )
        )
        rejected = await self.db.scalar(rejected_stmt) or 0

        pending_stmt = select(func.count(KnowledgeCandidate.id)).where(
            and_(
                KnowledgeCandidate.tenant_id == self.tenant_id,
                KnowledgeCandidate.status == "pending",
            )
        )
        pending = await self.db.scalar(pending_stmt) or 0

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": round(approved / total * 100, 2) if total > 0 else 0,
        }

    async def _get_candidate(self, candidate_id: str) -> KnowledgeCandidate:
        """获取候选知识"""
        stmt = select(KnowledgeCandidate).where(
            and_(
                KnowledgeCandidate.tenant_id == self.tenant_id,
                KnowledgeCandidate.candidate_id == candidate_id,
            )
        )
        result = await self.db.execute(stmt)
        candidate = result.scalar_one_or_none()
        if not candidate:
            raise ResourceNotFoundException("候选知识", candidate_id)
        return candidate
