"""
知识库设置模型
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class KnowledgeSettings(Base):
    """知识库设置表（每个租户一行）"""

    __tablename__ = "knowledge_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="租户ID"
    )
    embedding_model_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="嵌入模型ID（关联model_configs）"
    )
    rerank_model_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="重排模型ID（关联model_configs）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<KnowledgeSettings tenant={self.tenant_id}>"
