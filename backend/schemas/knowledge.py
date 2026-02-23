"""
知识库相关 Schema
"""
from datetime import datetime

from pydantic import AliasChoices, Field

from schemas.base import BaseSchema, TimestampSchema


# ============ 知识库 Schema ============
class KnowledgeBaseBase(BaseSchema):
    """知识库基础 Schema"""

    knowledge_type: str = Field(
        "faq", pattern="^(faq|doc|product|policy)$", description="知识类型(默认faq)"
    )
    title: str = Field(..., min_length=1, max_length=512, description="标题")
    content: str = Field(..., min_length=1, description="内容")
    category: str | None = Field(None, max_length=128, description="分类")
    tags: list[str] | None = Field(None, description="标签")
    source: str | None = Field(None, max_length=256, description="来源")
    source_url: str | None = Field(None, max_length=512, description="来源URL")
    priority: int = Field(0, ge=0, le=10, description="优先级")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识"""

    pass


class KnowledgeBaseUpdate(BaseSchema):
    """更新知识"""

    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    priority: int | None = None
    status: str | None = Field(None, pattern="^(active|inactive)$")


class KnowledgeBaseResponse(KnowledgeBaseBase, TimestampSchema):
    """知识库响应"""

    id: int
    knowledge_id: str
    tenant_id: str
    status: str
    version: int
    view_count: int
    use_count: int
    last_used_at: datetime | None
    quality_score: float | None
    reviewed: bool
    embedding_model: str | None = None
    embedding_status: str = "pending"
    chunk_count: int = 1


# ============ 知识库搜索 Schema ============
class KnowledgeSearchRequest(BaseSchema):
    """知识库搜索请求(支持POST body)"""

    query: str = Field(..., min_length=1, max_length=500, description="搜索关键词")
    knowledge_type: str | None = Field(None, description="知识类型过滤")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数")


# ============ RAG 检索 Schema ============
class RAGQueryRequest(BaseSchema):
    """RAG 查询请求"""

    query: str = Field(..., min_length=1, max_length=1000, description="查询问题")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数")
    filters: dict | None = Field(None, description="过滤条件")
    use_rerank: bool = Field(False, description="是否使用重排序")


class RAGQueryResponse(BaseSchema):
    """RAG 查询响应"""

    results: list[dict] = Field(..., description="检索结果")
    query_time: float = Field(..., description="查询耗时(秒)")


# ============ 知识库批量导入 Schema ============
class KnowledgeBatchImportRequest(BaseSchema):
    """批量导入知识库，支持 knowledge_items 或 items 字段"""

    knowledge_items: list[KnowledgeBaseCreate] = Field(
        ...,
        min_length=1,
        description="知识条目列表",
        validation_alias=AliasChoices("knowledge_items", "items"),
    )


class KnowledgeBatchImportResponse(BaseSchema):
    """批量导入响应"""

    success_count: int
    failed_count: int
    failed_items: list[dict] | None = None
    created: list[dict] | None = None  # 成功创建的知识条目(含knowledge_id)


# ============ 知识库设置 Schema ============
class KnowledgeSettingsUpdate(BaseSchema):
    """更新知识库设置"""

    embedding_model_id: int | None = None
    rerank_model_id: int | None = None


class KnowledgeSettingsResponse(BaseSchema):
    """知识库设置响应"""

    embedding_model_id: int | None = None
    rerank_model_id: int | None = None
    has_indexed_documents: bool = False
