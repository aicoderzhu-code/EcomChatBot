"""
候选知识 Schema
"""
from pydantic import Field

from schemas.base import BaseSchema, TimestampSchema


class KnowledgeCandidateResponse(TimestampSchema):
    """候选知识响应"""
    id: int
    candidate_id: str
    conversation_id: str
    question: str
    answer: str
    category: str | None
    confidence_score: float
    status: str
    approved_by: str | None
    created_knowledge_id: str | None
    rejection_reason: str | None


class ApproveRequest(BaseSchema):
    """审核通过请求"""
    category: str | None = None
    question: str | None = None
    answer: str | None = None


class RejectRequest(BaseSchema):
    """拒绝请求"""
    reason: str = Field(..., min_length=1, max_length=512)


class BatchApproveRequest(BaseSchema):
    """批量审核请求"""
    candidate_ids: list[str]
