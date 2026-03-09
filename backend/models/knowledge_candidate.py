"""
候选知识模型（从对话中自动提取）
"""
from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class KnowledgeCandidate(TenantBaseModel):
    """候选知识表"""

    __tablename__ = "knowledge_candidates"
    __table_args__ = (
        Index("idx_kc_tenant_status", "tenant_id", "status"),
        Index("idx_kc_conversation", "conversation_id"),
        Index("idx_kc_confidence", "confidence_score"),
        {"comment": "候选知识表（从对话自动提取）"},
    )

    candidate_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="候选知识唯一标识"
    )
    conversation_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="来源对话ID"
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="提取的问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="提取的答案")
    category: Mapped[str | None] = mapped_column(String(128), comment="推荐分类")
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="提取置信度(0-1)"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
        comment="状态(pending/approved/rejected)"
    )
    approved_by: Mapped[str | None] = mapped_column(String(64), comment="审核人")
    created_knowledge_id: Mapped[str | None] = mapped_column(
        String(64), comment="审核通过后关联的知识条目ID"
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(512), comment="拒绝原因")

    def __repr__(self) -> str:
        return f"<KnowledgeCandidate {self.candidate_id}: {self.question[:30]}>"
