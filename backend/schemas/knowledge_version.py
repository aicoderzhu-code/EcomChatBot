"""
知识库版本 Schema
"""
from pydantic import Field

from schemas.base import BaseSchema, TimestampSchema


class KnowledgeVersionResponse(TimestampSchema):
    """版本历史响应"""
    id: int
    version_id: str
    knowledge_id: str
    version_number: int
    title: str
    content: str
    category: str | None
    change_type: str
    change_summary: str | None
    changed_by: str | None


class VersionDiffResponse(BaseSchema):
    """版本对比响应"""
    knowledge_id: str
    version_from: int
    version_to: int
    title_changed: bool
    content_changed: bool
    category_changed: bool
    title_diff: dict | None = None
    content_diff: dict | None = None
    category_diff: dict | None = None
