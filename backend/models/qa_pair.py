"""
QA 对模型
"""
import json

from sqlalchemy import Float, Index, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class JSONEncodedList(TypeDecorator):
    """JSON List 类型"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class QAPair(TenantBaseModel):
    """QA 对表"""

    __tablename__ = "qa_pairs"
    __table_args__ = (
        Index("idx_qa_tenant_knowledge", "tenant_id", "knowledge_id"),
        Index("idx_qa_category", "category"),
        Index("idx_qa_status", "status"),
        {"comment": "QA问答对表"},
    )

    qa_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="QA对唯一标识"
    )
    knowledge_id: Mapped[str | None] = mapped_column(
        String(64), comment="关联知识库ID(type=faq)"
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="标准问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="标准答案")
    variations: Mapped[list | None] = mapped_column(
        JSONEncodedList, comment="相似问列表(JSON数组)"
    )
    category: Mapped[str | None] = mapped_column(String(128), comment="FAQ分类")
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级")
    use_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", comment="状态(active/inactive)"
    )

    def __repr__(self) -> str:
        return f"<QAPair {self.qa_id}: {self.question[:30]}>"
