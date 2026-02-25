"""
知识库相关模型
"""
import json
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class JSONEncodedList(TypeDecorator):
    """跨数据库兼容的 JSON List 类型，自动序列化/反序列化"""
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


class KnowledgeBase(TenantBaseModel):
    """知识库表"""

    __tablename__ = "knowledge_base"
    __table_args__ = (
        Index("idx_knowledge_tenant_type", "tenant_id", "knowledge_type"),
        Index("idx_knowledge_category", "category"),
        Index("idx_knowledge_status", "status"),
        {"comment": "知识库表"},
    )

    # 知识标识
    knowledge_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="知识条目ID"
    )

    # 知识类型
    knowledge_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="类型(faq/doc/product/policy)"
    )

    # 标题和内容
    title: Mapped[str] = mapped_column(String(512), nullable=False, comment="标题/问题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容/答案")

    # 分类和标签
    category: Mapped[str | None] = mapped_column(String(128), comment="分类")
    tags: Mapped[list | None] = mapped_column(JSONEncodedList, comment="标签(JSON数组)")

    # 来源
    source: Mapped[str | None] = mapped_column(String(256), comment="来源")
    source_url: Mapped[str | None] = mapped_column(String(512), comment="来源URL")

    # 向量化
    embedding_vector_id: Mapped[str | None] = mapped_column(
        String(128), comment="Milvus向量ID"
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(64), comment="使用的Embedding模型"
    )
    embedding_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", comment="向量化状态(pending/completed/failed)"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, default=1, comment="文本切片数量"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, default=0, comment="原始文件字节数"
    )

    # 优先级和状态
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", comment="状态(active/inactive)"
    )

    # 版本控制
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")
    parent_id: Mapped[str | None] = mapped_column(String(64), comment="父知识ID(用于版本管理)")

    # 使用统计
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="查看次数")
    use_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后使用时间")

    # 质量评分
    quality_score: Mapped[float | None] = mapped_column(Float, comment="质量评分")

    # 审核信息
    reviewed: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="是否已审核"
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(64), comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")

    def __repr__(self) -> str:
        return f"<KnowledgeBase {self.title} ({self.knowledge_type})>"


class KnowledgeUsageLog(TenantBaseModel):
    """知识库使用日志"""

    __tablename__ = "knowledge_usage_logs"
    __table_args__ = (
        Index("idx_usage_knowledge", "knowledge_id"),
        Index("idx_usage_conversation", "conversation_id"),
        Index("idx_usage_created", "created_at"),
        {"comment": "知识库使用日志表"},
    )

    # 关联信息
    knowledge_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="知识ID")
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话ID")
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="消息ID")

    # 查询信息
    query: Mapped[str] = mapped_column(Text, nullable=False, comment="用户查询")

    # 匹配信息
    match_score: Mapped[float | None] = mapped_column(Float, comment="匹配分数")
    match_method: Mapped[str | None] = mapped_column(
        String(32), comment="匹配方法(vector_search/keyword_search等)"
    )

    # 用户反馈
    helpful: Mapped[bool | None] = mapped_column(comment="是否有帮助")
    feedback: Mapped[str | None] = mapped_column(Text, comment="用户反馈")

    def __repr__(self) -> str:
        return f"<KnowledgeUsageLog {self.knowledge_id}>"
