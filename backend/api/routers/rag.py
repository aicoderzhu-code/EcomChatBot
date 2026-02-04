"""
RAG（检索增强生成）API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel

from api.dependencies import DBDep, TenantDep
from schemas import ApiResponse
from services import RAGService

router = APIRouter(prefix="/rag", tags=["RAG 检索增强"])


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""

    query: str
    top_k: int = 5
    use_vector_search: bool = True  # 是否使用向量搜索


class RAGGenerateRequest(BaseModel):
    """RAG 生成请求"""

    query: str
    use_vector_search: bool = True


class IndexKnowledgeRequest(BaseModel):
    """索引知识库请求"""

    knowledge_id: str


class BatchIndexRequest(BaseModel):
    """批量索引请求"""

    knowledge_ids: list[str]


@router.post("/retrieve", response_model=ApiResponse[list[dict]])
async def rag_retrieve(
    request: RAGQueryRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    RAG 检索接口
    
    从知识库中检索相关内容（支持向量检索）
    """
    service = RAGService(db, tenant_id)

    results = await service.retrieve(
        query=request.query,
        top_k=request.top_k,
        use_vector_search=request.use_vector_search,
    )

    return ApiResponse(data=results)


@router.post("/generate", response_model=ApiResponse[dict])
async def rag_generate(
    request: RAGGenerateRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    RAG 生成接口
    
    检索相关知识并生成回复
    """
    service = RAGService(db, tenant_id)

    result = await service.retrieve_and_generate(
        query=request.query,
        use_vector_search=request.use_vector_search,
    )

    return ApiResponse(data=result)


@router.post("/index", response_model=ApiResponse[dict])
async def index_knowledge(
    request: IndexKnowledgeRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    为知识库项创建向量索引
    
    将知识库内容向量化并存入 Milvus
    """
    service = RAGService(db, tenant_id)

    result = await service.index_knowledge(request.knowledge_id)

    return ApiResponse(data=result)


@router.post("/index-batch", response_model=ApiResponse[dict])
async def batch_index_knowledge(
    request: BatchIndexRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    批量索引知识库
    
    为多个知识库项创建向量索引
    """
    service = RAGService(db, tenant_id)

    result = await service.index_batch_knowledge(request.knowledge_ids)

    return ApiResponse(data=result)


@router.get("/stats", response_model=ApiResponse[dict])
async def get_rag_stats(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    获取 RAG 统计信息
    
    包括向量库统计、Embedding 模型信息等
    """
    service = RAGService(db, tenant_id)

    stats = service.get_stats()

    return ApiResponse(data=stats)
