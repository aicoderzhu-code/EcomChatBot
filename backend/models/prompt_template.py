"""提示词模板模型"""
from enum import Enum as PyEnum

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class TemplateType(str, PyEnum):
    """模板类型"""
    POSTER = "poster"
    VIDEO = "video"
    TITLE = "title"
    DESCRIPTION = "description"


class PromptTemplate(TenantBaseModel):
    """提示词模板表"""

    __tablename__ = "prompt_templates"
    __table_args__ = (
        Index("idx_prompt_template_tenant", "tenant_id"),
        Index("idx_prompt_template_type", "template_type"),
        {"comment": "提示词模板表"},
    )

    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="模板名称"
    )
    template_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="模板类型(poster/video/title/description)"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="模板内容(含变量占位符)"
    )
    variables: Mapped[list | None] = mapped_column(
        JSONField, comment="变量列表(JSON)"
    )
    is_default: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否为默认模板"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="使用次数"
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name} ({self.template_type})>"
