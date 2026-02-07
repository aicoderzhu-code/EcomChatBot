"""
知识库管理 API 路由
"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantDep
from api.middleware import StorageQuotaDep, ApiQuotaDep
from schemas import (
    ApiResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeBatchImportRequest,
    KnowledgeBatchImportResponse,
    PaginatedResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from services.knowledge_service import KnowledgeService
from services.rag_service import RAGService

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


@router.post("/create", response_model=ApiResponse[KnowledgeBaseResponse])
async def create_knowledge(
    knowledge_data: KnowledgeBaseCreate,
    tenant_id: StorageQuotaDep,  # 检查存储配额
    db: DBDep,
):
    """
    创建知识条目

    ⚠️ 会检查存储空间配额
    """
    service = KnowledgeService(db, tenant_id)
    knowledge = await service.create_knowledge(
        knowledge_type=knowledge_data.knowledge_type,
        title=knowledge_data.title,
        content=knowledge_data.content,
        category=knowledge_data.category,
        tags=knowledge_data.tags,
        source=knowledge_data.source,
        priority=knowledge_data.priority,
    )
    return ApiResponse(data=knowledge)


@router.get("/list", response_model=ApiResponse[PaginatedResponse[KnowledgeBaseResponse]])
async def list_knowledge(
    tenant_id: TenantDep,
    db: DBDep,
    knowledge_type: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询知识列表"""
    service = KnowledgeService(db, tenant_id)
    knowledge_list, total = await service.list_knowledge(
        knowledge_type=knowledge_type,
        category=category,
        keyword=keyword,
        page=page,
        size=size,
    )

    paginated = PaginatedResponse.create(
        items=knowledge_list,
        total=total,
        page=page,
        size=size,
    )

    return ApiResponse(data=paginated)


@router.get("/{knowledge_id}", response_model=ApiResponse[KnowledgeBaseResponse])
async def get_knowledge(
    knowledge_id: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取知识详情"""
    service = KnowledgeService(db, tenant_id)
    knowledge = await service.get_knowledge(knowledge_id)
    return ApiResponse(data=knowledge)


@router.put("/{knowledge_id}", response_model=ApiResponse[KnowledgeBaseResponse])
async def update_knowledge(
    knowledge_id: str,
    knowledge_data: KnowledgeBaseUpdate,
    tenant_id: StorageQuotaDep,  # 检查存储配额
    db: DBDep,
):
    """
    更新知识条目

    ⚠️ 会检查存储空间配额
    """
    service = KnowledgeService(db, tenant_id)
    knowledge = await service.update_knowledge(
        knowledge_id=knowledge_id,
        title=knowledge_data.title,
        content=knowledge_data.content,
        category=knowledge_data.category,
        tags=knowledge_data.tags,
        priority=knowledge_data.priority,
    )
    return ApiResponse(data=knowledge)


@router.delete("/{knowledge_id}", response_model=ApiResponse[dict])
async def delete_knowledge(
    knowledge_id: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """删除知识条目"""
    service = KnowledgeService(db, tenant_id)
    await service.delete_knowledge(knowledge_id)
    return ApiResponse(data={"message": "删除成功"})


@router.post("/batch-import", response_model=ApiResponse[KnowledgeBatchImportResponse])
async def batch_import_knowledge(
    import_data: KnowledgeBatchImportRequest,
    tenant_id: StorageQuotaDep,  # 检查存储配额
    db: DBDep,
):
    """
    批量导入知识

    ⚠️ 会检查存储空间配额
    """
    service = KnowledgeService(db, tenant_id)
    results = await service.batch_import(
        knowledge_items=[item.model_dump() for item in import_data.knowledge_items]
    )

    response = KnowledgeBatchImportResponse(
        success_count=len(results["success"]),
        failed_count=len(results["failed"]),
        failed_items=results["failed"] if results["failed"] else None,
    )

    return ApiResponse(data=response)


@router.post("/search", response_model=ApiResponse[list[KnowledgeBaseResponse]])
async def search_knowledge(
    query: str = Query(..., description="搜索关键词"),
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
    knowledge_type: str | None = None,
    top_k: int = Query(5, ge=1, le=20),
):
    """
    搜索知识

    ⚠️ 会检查API调用配额
    """
    service = KnowledgeService(db, tenant_id)
    knowledge_list = await service.search_knowledge(
        query=query,
        knowledge_type=knowledge_type,
        top_k=top_k,
    )
    return ApiResponse(data=knowledge_list)


@router.post("/rag/query", response_model=ApiResponse[dict])
async def rag_query(
    query_data: RAGQueryRequest,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    RAG 查询（检索增强生成）

    注：当前为简化实现，实际应集成 LangChain 和 Milvus

    ⚠️ 会检查API调用配额
    """
    service = RAGService(db, tenant_id)
    results = await service.retrieve(
        query=query_data.query,
        top_k=query_data.top_k,
    )

    return ApiResponse(
        data={
            "results": results,
            "query_time": 0.1,  # TODO: 实际查询时间
        }
    )
