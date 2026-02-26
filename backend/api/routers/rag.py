"""
RAG（检索增强生成）API 路由
"""
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.dependencies import DBDep, TenantDep
from api.middleware import ApiQuotaDep, StorageQuotaDep
from models.model_config import ModelConfig
from schemas import ApiResponse
from services import RAGService
from services.knowledge_service import KnowledgeService
from services.llm_service import LLMService
from services.model_config_service import ModelConfigService
from services.prompt_service import PromptService

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


async def _load_embedding_config(db, tenant_id):
    """从 KnowledgeSettings 加载 embedding 模型配置"""
    try:
        ks = await KnowledgeService(db, tenant_id).get_settings()
        if ks and ks.embedding_model_id:
            result = await db.execute(select(ModelConfig).where(ModelConfig.id == ks.embedding_model_id))
            return result.scalar_one_or_none()
    except Exception:
        pass
    return None


@router.post("/retrieve", response_model=ApiResponse[list[dict]])
async def rag_retrieve(
    request: RAGQueryRequest,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    RAG 检索接口

    从知识库中检索相关内容（支持向量检索）

    ⚠️ 会检查API调用配额
    """
    service = RAGService(db, tenant_id, embedding_model_config=await _load_embedding_config(db, tenant_id))

    results = await service.retrieve(
        query=request.query,
        top_k=request.top_k,
        use_vector_search=request.use_vector_search,
    )

    return ApiResponse(data=results)


@router.post("/generate", response_model=ApiResponse[dict])
async def rag_generate(
    request: RAGGenerateRequest,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    RAG 生成接口

    检索相关知识并生成回复

    ⚠️ 会检查API调用配额
    """
    service = RAGService(db, tenant_id, embedding_model_config=await _load_embedding_config(db, tenant_id))

    result = await service.retrieve_and_generate(
        query=request.query,
        use_vector_search=request.use_vector_search,
    )

    return ApiResponse(data=result)


@router.post("/index", response_model=ApiResponse[dict])
async def index_knowledge(
    request: IndexKnowledgeRequest,
    tenant_id: StorageQuotaDep,  # 检查存储配额
    db: DBDep,
):
    """
    为知识库项创建向量索引

    将知识库内容向量化并存入 Milvus

    ⚠️ 会检查存储空间配额
    """
    service = RAGService(db, tenant_id, embedding_model_config=await _load_embedding_config(db, tenant_id))

    result = await service.index_knowledge(request.knowledge_id)

    return ApiResponse(data=result)


@router.post("/index-batch", response_model=ApiResponse[dict])
async def batch_index_knowledge(
    request: BatchIndexRequest,
    tenant_id: StorageQuotaDep,  # 检查存储配额
    db: DBDep,
):
    """
    批量索引知识库

    为多个知识库项创建向量索引

    ⚠️ 会检查存储空间配额
    """
    service = RAGService(db, tenant_id, embedding_model_config=await _load_embedding_config(db, tenant_id))

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
    service = RAGService(db, tenant_id, embedding_model_config=await _load_embedding_config(db, tenant_id))

    stats = service.get_stats()

    return ApiResponse(data=stats)


class RAGTestRequest(BaseModel):
    """端到端 RAG 测试请求"""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    use_rerank: bool = False
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0)
    model_config_id: int | None = Field(None, description="LLM 模型配置ID，不传则使用默认模型")


@router.post("/test", response_model=ApiResponse[dict])
async def rag_end_to_end_test(
    request: RAGTestRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    端到端 RAG 测试

    执行完整的 RAG 流程：检索 + 生成，返回分段耗时和详细指标。
    LLM 模型从系统设置的模型配置加载。
    """
    total_start = time.monotonic()

    # 1. Retrieval phase
    retrieval_start = time.monotonic()
    rag_service = RAGService(
        db, tenant_id,
        embedding_model_config=await _load_embedding_config(db, tenant_id),
    )
    retrieval_results = await rag_service.retrieve(
        query=request.query,
        top_k=request.top_k,
        use_vector_search=True,
    )
    retrieval_ms = int((time.monotonic() - retrieval_start) * 1000)

    if request.similarity_threshold > 0:
        retrieval_results = [
            r for r in retrieval_results
            if r.get("score", 0) >= request.similarity_threshold
        ]

    # 2. Build context from retrieval results
    context_parts = []
    rag_sources = []
    for r in retrieval_results:
        title = r.get("title", "")
        content = r.get("content", "")
        context_parts.append(f"[{title}]\n{content}")
        rag_sources.append({
            "title": title,
            "score": r.get("score", 0),
            "chunk_preview": content[:150] if content else "",
        })

    context = "\n\n".join(context_parts)

    # 3. LLM generation phase
    generation_start = time.monotonic()
    mc_svc = ModelConfigService(db, tenant_id)
    if request.model_config_id:
        mc = await mc_svc.get_model_config(request.model_config_id)
    else:
        mc = await mc_svc.get_default_model(use_case="dialogue")

    llm_service = LLMService(tenant_id, model_config=mc)
    prompt_service = PromptService()
    system_prompt = prompt_service.get_system_prompt()

    user_content = request.query
    if context:
        user_content = f"{request.query}\n\n参考以下知识库内容：\n{context}"

    generated_response = await llm_service.generate_response(
        messages=[{"role": "user", "content": user_content}],
        system_prompt=system_prompt,
    )
    generation_ms = int((time.monotonic() - generation_start) * 1000)

    total_ms = int((time.monotonic() - total_start) * 1000)

    return ApiResponse(data={
        "retrieval_results": retrieval_results,
        "generated_response": generated_response,
        "model": llm_service.model_name,
        "provider": llm_service._provider,
        "timing": {
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        },
        "token_usage": {
            "input_tokens": llm_service.count_tokens(user_content),
            "output_tokens": llm_service.count_tokens(generated_response),
        },
        "rag_sources": rag_sources,
    })
