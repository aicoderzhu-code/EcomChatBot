"""
Playground API - 大模型测试接口
不创建会话/消息记录，不消耗对话配额
"""
import json
import time
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.dependencies import DBDep, TenantDep
from schemas import ApiResponse
from services.llm_service import LLMService
from services.model_config_service import ModelConfigService
from services.knowledge_service import KnowledgeService
from services.prompt_service import PromptService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playground", tags=["Playground 测试"])


class PlaygroundChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    model_config_id: int | None = Field(None, description="模型配置ID，不传则使用默认模型")
    system_prompt: str | None = Field(None, description="自定义系统提示词")
    use_rag: bool = False
    rag_top_k: int = Field(3, ge=1, le=10)
    conversation_history: list[dict] | None = Field(None, description="多轮历史 [{role, content}]")

    model_config = {"json_schema_extra": {"examples": [{"message": "你好"}]}}


class PlaygroundChatResponse(BaseModel):
    response: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    response_time_ms: int
    used_rag: bool = False
    rag_sources: list[dict] | None = None


async def _load_llm_service(db, tenant_id: str, model_config_id: int | None) -> LLMService:
    """Load LLMService from DB model config or fall back to default."""
    svc = ModelConfigService(db, tenant_id)
    if model_config_id:
        mc = await svc.get_model_config(model_config_id)
    else:
        mc = await svc.get_default_model(use_case="dialogue")
    return LLMService(tenant_id, model_config=mc)


@router.post("/chat", response_model=ApiResponse[PlaygroundChatResponse])
async def playground_chat(
    request: PlaygroundChatRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    Playground 对话（同步）

    从「系统设置 > 模型配置」加载模型，不创建会话记录，不消耗配额。
    """
    start = time.monotonic()

    llm_service = await _load_llm_service(db, tenant_id, request.model_config_id)

    prompt_service = PromptService()
    system_prompt = request.system_prompt or prompt_service.get_system_prompt()

    messages: list[dict] = []
    if request.conversation_history:
        messages.extend(request.conversation_history)

    rag_sources: list[dict] = []

    if request.use_rag:
        ks = KnowledgeService(db, tenant_id)
        knowledge_list = await ks.search_knowledge(query=request.message, top_k=request.rag_top_k)
        if knowledge_list:
            context = "\n\n".join(f"[{k.title}]\n{k.content}" for k in knowledge_list)
            messages.append({"role": "user", "content": f"{request.message}\n\n参考以下知识库内容：\n{context}"})
            rag_sources = [
                {"title": k.title, "score": 0.9, "chunk_preview": (k.content or "")[:120]}
                for k in knowledge_list
            ]
        else:
            messages.append({"role": "user", "content": request.message})
    else:
        messages.append({"role": "user", "content": request.message})

    response_text = await llm_service.generate_response(messages, system_prompt)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return ApiResponse(data=PlaygroundChatResponse(
        response=response_text,
        model=llm_service.model_name,
        provider=llm_service._provider,
        input_tokens=llm_service.count_tokens(request.message),
        output_tokens=llm_service.count_tokens(response_text),
        response_time_ms=elapsed_ms,
        used_rag=request.use_rag,
        rag_sources=rag_sources or None,
    ))


@router.post("/chat-stream")
async def playground_chat_stream(
    request: PlaygroundChatRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    Playground 流式对话（SSE 事件流）

    事件类型: chunk / sources / done / error
    """
    async def sse_generator():
        start = time.monotonic()
        try:
            llm_service = await _load_llm_service(db, tenant_id, request.model_config_id)

            prompt_service = PromptService()
            system_prompt = request.system_prompt or prompt_service.get_system_prompt()

            messages: list[dict] = []
            if request.conversation_history:
                messages.extend(request.conversation_history)

            rag_sources: list[dict] = []

            if request.use_rag:
                ks = KnowledgeService(db, tenant_id)
                knowledge_list = await ks.search_knowledge(query=request.message, top_k=request.rag_top_k)
                if knowledge_list:
                    rag_sources = [
                        {"title": k.title, "score": 0.9, "chunk_preview": (k.content or "")[:120]}
                        for k in knowledge_list
                    ]
                    yield f"event: sources\ndata: {json.dumps({'sources': rag_sources}, ensure_ascii=False)}\n\n"

                    context = "\n\n".join(f"[{k.title}]\n{k.content}" for k in knowledge_list)
                    messages.append({"role": "user", "content": f"{request.message}\n\n参考以下知识库内容：\n{context}"})
                else:
                    messages.append({"role": "user", "content": request.message})
            else:
                messages.append({"role": "user", "content": request.message})

            idx = 0
            async for chunk in llm_service.astream(messages, system_prompt):
                if chunk["type"] == "chunk":
                    yield f"event: chunk\ndata: {json.dumps({'content': chunk['content'], 'index': idx}, ensure_ascii=False)}\n\n"
                    idx += 1
                elif chunk["type"] == "done":
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    done_data = {
                        "model": chunk.get("model", ""),
                        "provider": chunk.get("provider", ""),
                        "input_tokens": chunk.get("input_tokens", 0),
                        "output_tokens": chunk.get("output_tokens", 0),
                        "total_tokens": chunk.get("input_tokens", 0) + chunk.get("output_tokens", 0),
                        "response_time_ms": elapsed_ms,
                        "used_rag": request.use_rag,
                    }
                    yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("Playground stream error: %s", e, exc_info=True)
            yield f"event: error\ndata: {json.dumps({'code': 'INTERNAL_ERROR', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
