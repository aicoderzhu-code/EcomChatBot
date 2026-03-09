"""
QA 对 Schema
"""
from pydantic import Field

from schemas.base import BaseSchema, TimestampSchema


class QAPairCreate(BaseSchema):
    """创建 QA 对"""
    question: str = Field(..., min_length=1, max_length=2000, description="标准问题")
    answer: str = Field(..., min_length=1, max_length=4000, description="标准答案")
    category: str | None = Field(None, max_length=128, description="分类")
    priority: int = Field(0, ge=0, description="优先级")
    knowledge_id: str | None = Field(None, description="关联知识库ID")


class QAPairUpdate(BaseSchema):
    """更新 QA 对"""
    question: str | None = Field(None, min_length=1, max_length=2000)
    answer: str | None = Field(None, min_length=1, max_length=4000)
    category: str | None = None
    priority: int | None = None
    variations: list[str] | None = None
    status: str | None = Field(None, pattern="^(active|inactive)$")


class QAPairResponse(TimestampSchema):
    """QA 对响应"""
    id: int
    qa_id: str
    knowledge_id: str | None
    question: str
    answer: str
    variations: list[str] | None
    category: str | None
    priority: int
    use_count: int
    status: str


class QAImportItem(BaseSchema):
    """CSV 导入项"""
    question: str
    answer: str
    category: str | None = None
