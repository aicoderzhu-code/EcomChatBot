"""
知识库版本历史模型
"""
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class KnowledgeVersion(TenantBaseModel):
    """知识库版本历史表"""

    __tablename__ = "knowledge_versions"
    __table_args__ = (
        Index("idx_kv_knowledge_id", "knowledge_id"),
        Index("idx_kv_knowledge_version", "knowledge_id", "version_number"),
        {"comment": "知识库版本历史表"},
    )

    version_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="版本唯一标识"
    )
    knowledge_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="关联知识条目ID"
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号"
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="快照：标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="快照：内容")
    category: Mapped[str | None] = mapped_column(String(128), comment="快照：分类")
    change_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="变更类型(create/update/rollback)"
    )
    change_summary: Mapped[str | None] = mapped_column(
        String(512), comment="变更说明"
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(64), comment="操作人"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeVersion {self.knowledge_id} v{self.version_number}>"
