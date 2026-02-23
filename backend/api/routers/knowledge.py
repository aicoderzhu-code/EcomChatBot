"""
知识库管理 API 路由
"""
from fastapi import APIRouter, Body, Query, UploadFile, File, Form
from sqlalchemy import select

from api.dependencies import DBDep, TenantFlexDep
from api.middleware import StorageQuotaDep, ApiQuotaDep
from models.model_config import ModelConfig
from schemas import (
    ApiResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeBatchImportRequest,
    KnowledgeBatchImportResponse,
    KnowledgeSettingsResponse,
    KnowledgeSettingsUpdate,
    PaginatedResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from schemas.knowledge import KnowledgeSearchRequest
from services.document_parser import parse_and_split
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
    tenant_id: TenantFlexDep,
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

    created_list = [
        {"knowledge_id": k.knowledge_id, "title": k.title}
        for k in results["success"]  # 现为 KnowledgeBase 对象列表
    ]
    response = KnowledgeBatchImportResponse(
        success_count=len(results["success"]),
        failed_count=len(results["failed"]),
        failed_items=results["failed"] if results["failed"] else None,
        created=created_list,
    )

    return ApiResponse(data=response)


@router.post("/search", response_model=ApiResponse[list[KnowledgeBaseResponse]])
async def search_knowledge(
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
    search_data: KnowledgeSearchRequest | None = Body(None),
    query: str = Query(None, description="搜索关键词(URL参数)"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数"),
):
    """
    搜索知识，支持 POST body 或 URL 参数

    ⚠️ 会检查API调用配额
    """
    if search_data:
        query_str = search_data.query
        top_k_val = search_data.top_k
        knowledge_type = search_data.knowledge_type
    else:
        if not query:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="query 参数必填")
        query_str = query
        top_k_val = top_k
        knowledge_type = None

    service = KnowledgeService(db, tenant_id)
    knowledge_list = await service.search_knowledge(
        query=query_str,
        knowledge_type=knowledge_type,
        top_k=top_k_val,
    )
    return ApiResponse(data=knowledge_list)


@router.post("/upload", response_model=ApiResponse[KnowledgeBaseResponse])
async def upload_document(
    file: UploadFile = File(...),
    category: str | None = Form(None),
    tags: str | None = Form(None),  # 逗号分隔的字符串
    tenant_id: StorageQuotaDep = None,
    db: DBDep = None,
):
    """上传文件并使用 LangChain 解析、切片后存入知识库"""
    file_bytes = await file.read()
    filename = file.filename or "unknown"

    content, chunk_count = await parse_and_split(filename, file_bytes)

    service = KnowledgeService(db, tenant_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    item = await service.create_knowledge(
        knowledge_type="doc",
        title=filename,
        content=content,
        category=category,
        tags=tag_list,
        source="upload",
    )
    item.chunk_count = chunk_count
    await db.commit()
    await db.refresh(item)

    return ApiResponse(data=KnowledgeBaseResponse.model_validate(item))


# ============ 知识库设置 - 固定路径必须在 /{knowledge_id} 之前 ============

@router.get("/settings", response_model=ApiResponse[KnowledgeSettingsResponse])
async def get_knowledge_settings(tenant_id: TenantFlexDep, db: DBDep):
    """获取知识库设置"""
    svc = KnowledgeService(db, tenant_id)
    s = await svc.get_settings()
    has_indexed = await svc.has_indexed_documents()
    return ApiResponse(data=KnowledgeSettingsResponse(
        embedding_model_id=s.embedding_model_id,
        rerank_model_id=s.rerank_model_id,
        has_indexed_documents=has_indexed,
    ))


@router.put("/settings", response_model=ApiResponse[KnowledgeSettingsResponse])
async def update_knowledge_settings(
    settings_data: KnowledgeSettingsUpdate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新知识库设置（有向量化文档时不允许换 embedding 模型）"""
    svc = KnowledgeService(db, tenant_id)
    s = await svc.update_settings(
        embedding_model_id=settings_data.embedding_model_id,
        rerank_model_id=settings_data.rerank_model_id,
    )
    has_indexed = await svc.has_indexed_documents()
    return ApiResponse(data=KnowledgeSettingsResponse(
        embedding_model_id=s.embedding_model_id,
        rerank_model_id=s.rerank_model_id,
        has_indexed_documents=has_indexed,
    ))


@router.post("/rag/query", response_model=ApiResponse[dict])
async def rag_query(
    query_data: RAGQueryRequest,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    RAG 查询（检索增强生成）

    ⚠️ 会检查API调用配额
    """
    # 从 knowledge_settings 加载 embedding / rerank 配置
    knowledge_svc = KnowledgeService(db, tenant_id)
    ks = await knowledge_svc.get_settings()

    # 加载 embedding model config（优先使用租户配置）
    embedding_config = None
    if ks.embedding_model_id:
        mc_stmt = select(ModelConfig).where(ModelConfig.id == ks.embedding_model_id)
        mc_result = await db.execute(mc_stmt)
        embedding_config = mc_result.scalar_one_or_none()

    # 加载 rerank model config（仅在请求时使用）
    rerank_config = None
    if query_data.use_rerank and ks.rerank_model_id:
        mc_stmt = select(ModelConfig).where(ModelConfig.id == ks.rerank_model_id)
        mc_result = await db.execute(mc_stmt)
        rerank_config = mc_result.scalar_one_or_none()

    service = RAGService(
        db,
        tenant_id,
        embedding_model_config=embedding_config,
        rerank_model_config=rerank_config,
    )
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


# ============ 固定路径结束，参数路径在最后 ============

@router.get("/{knowledge_id}", response_model=ApiResponse[KnowledgeBaseResponse])
async def get_knowledge(
    knowledge_id: str,
    tenant_id: TenantFlexDep,
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
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除知识条目"""
    service = KnowledgeService(db, tenant_id)
    await service.delete_knowledge(knowledge_id)
    return ApiResponse(data={"message": "删除成功"})
