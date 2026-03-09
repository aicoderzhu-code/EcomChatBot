"""
AI 智能对话 API 路由 - 集成 LangChain
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from api.dependencies import DBDep, TenantFlexDep
from api.middleware import ConversationQuotaDep, ApiQuotaDep
from schemas import ApiResponse
from services import ConversationChainService, simple_chat
from services.knowledge_service import KnowledgeService
from services.quota_service import QuotaService, QuotaExceededError

router = APIRouter(prefix="/ai-chat", tags=["AI 智能对话"])


class ChatRequest(BaseModel):
    """对话请求"""

    conversation_id: str
    message: str
    use_rag: bool = False  # 是否使用 RAG
    rag_top_k: int = 3  # RAG 检索数量


class ChatResponse(BaseModel):
    """对话响应"""

    response: str
    conversation_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    used_rag: bool = False
    sources: list[dict] | None = None


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def ai_chat(
    request: ChatRequest,
    tenant_id: ConversationQuotaDep,  # 检查对话次数配额
    db: DBDep,
):
    """
    AI 智能对话接口

    ⚠️ 会检查对话次数配额

    支持：
    - 基于 LangChain 的对话
    - 自动记忆管理
    - RAG 知识库检索
    """
    try:
        # 检查AI回复配额
        quota_service = QuotaService(db)
        try:
            await quota_service.check_reply_quota(tenant_id)
        except QuotaExceededError as e:
            return ApiResponse(
                success=False,
                error={"code": "QUOTA_EXCEEDED", "message": str(e)},
            )

        knowledge_items = None

        # 如果使用 RAG，先检索知识库
        if request.use_rag:
            knowledge_service = KnowledgeService(db, tenant_id)
            knowledge_list = await knowledge_service.search_knowledge(
                query=request.message,
                top_k=request.rag_top_k,
            )

            # 转换为字典格式
            knowledge_items = [
                {
                    "knowledge_id": k.knowledge_id,
                    "title": k.title,
                    "content": k.content,
                    "category": k.category,
                    "source": k.source,
                }
                for k in knowledge_list
            ]

        # 调用对话服务
        result = await simple_chat(
            db=db,
            tenant_id=tenant_id,
            conversation_id=request.conversation_id,
            user_input=request.message,
            use_rag=request.use_rag,
            knowledge_items=knowledge_items,
        )

        # 构建响应
        response_data = ChatResponse(
            response=result["response"],
            conversation_id=request.conversation_id,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            total_tokens=result["total_tokens"],
            model=result["model"],
            used_rag=request.use_rag,
            sources=result.get("sources"),
        )

        # 扣减配额
        await quota_service.increment_reply(tenant_id)
        await db.commit()

        return ApiResponse(data=response_data)

    except QuotaExceededError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


@router.post("/chat-stream")
async def ai_chat_stream(
    request: ChatRequest,
    tenant_id: ConversationQuotaDep,
    db: DBDep,
):
    """
    AI 智能对话流式接口（标准 SSE 事件流）

    ⚠️ 会检查对话次数配额

    事件类型: chunk / sources / done / error
    """
    # 检查AI回复配额（在生成器外部检查，尽早返回错误）
    quota_service = QuotaService(db)
    try:
        await quota_service.check_reply_quota(tenant_id)
    except QuotaExceededError as e:
        async def quota_error_gen():
            error_data = {"code": "QUOTA_EXCEEDED", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            quota_error_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    async def sse_generator():
        try:
            # 1. RAG retrieval (if enabled)
            rag_sources: list[dict] = []
            knowledge_items = None
            if request.use_rag:
                knowledge_service = KnowledgeService(db, tenant_id)
                knowledge_list = await knowledge_service.search_knowledge(
                    query=request.message,
                    top_k=request.rag_top_k,
                )
                knowledge_items = [
                    {
                        "knowledge_id": k.knowledge_id,
                        "title": k.title,
                        "content": k.content,
                        "category": k.category,
                        "source": k.source,
                    }
                    for k in knowledge_list
                ]
                rag_sources = [
                    {"title": k.title, "score": 0.9, "chunk_preview": (k.content or "")[:120]}
                    for k in knowledge_list
                ]
                yield f"event: sources\ndata: {json.dumps({'sources': rag_sources}, ensure_ascii=False)}\n\n"

            # 2. Build conversation chain and messages
            chain = ConversationChainService(
                db=db, tenant_id=tenant_id,
                conversation_id=request.conversation_id,
            )
            await chain.initialize()

            if request.use_rag and knowledge_items:
                context = chain.prompt_service.build_context_from_knowledge(knowledge_items)
                user_content = f"{request.message}\n\n参考以下知识库内容：\n{context}"
            else:
                user_content = request.message

            messages = chain.memory.get_chat_history()
            messages.append({"role": "user", "content": user_content})
            system_prompt = chain.prompt_service.get_system_prompt()

            # 3. Real streaming via LLMService.astream()
            idx = 0
            full_response = ""
            async for chunk in chain.llm_service.astream(messages, system_prompt):
                if chunk["type"] == "chunk":
                    yield f"event: chunk\ndata: {json.dumps({'content': chunk['content'], 'index': idx}, ensure_ascii=False)}\n\n"
                    full_response += chunk["content"]
                    idx += 1
                elif chunk["type"] == "done":
                    done_data = {
                        "conversation_id": request.conversation_id,
                        "model": chunk.get("model", ""),
                        "provider": chunk.get("provider", ""),
                        "input_tokens": chunk.get("input_tokens", 0),
                        "output_tokens": chunk.get("output_tokens", 0),
                        "total_tokens": chunk.get("input_tokens", 0) + chunk.get("output_tokens", 0),
                        "used_rag": request.use_rag,
                    }
                    yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

            # 4. Persist messages and update memory (after stream completes)
            chain.memory.add_user_message(request.message)
            chain.memory.add_ai_message(full_response)

            # 5. 扣减配额
            await quota_service.increment_reply(tenant_id)
            await db.commit()

        except Exception as e:
            error_data = {"code": "INTERNAL_ERROR", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/classify-intent", response_model=ApiResponse[dict])
async def classify_intent(
    conversation_id: str,
    message: str,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    意图分类接口

    识别用户消息的意图类别

    ⚠️ 会检查API调用配额
    """
    try:
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

        intent = await chain.classify_intent(message)

        return ApiResponse(
            data={
                "intent": intent,
                "message": message,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"意图识别失败: {str(e)}")


@router.post("/extract-entities", response_model=ApiResponse[dict])
async def extract_entities(
    conversation_id: str,
    message: str,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    实体提取接口

    从用户消息中提取关键实体（订单号、商品名等）

    ⚠️ 会检查API调用配额
    """
    try:
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

        entities = await chain.extract_entities(message)

        return ApiResponse(
            data={
                "entities": entities,
                "message": message,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体提取失败: {str(e)}")


@router.get("/conversation/{conversation_id}/summary", response_model=ApiResponse[dict])
async def get_conversation_summary(
    conversation_id: str,
    tenant_id: ApiQuotaDep,  # 检查API调用配额
    db: DBDep,
):
    """
    获取对话摘要

    返回当前对话的简要摘要

    ⚠️ 会检查API调用配额
    """
    try:
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

        await chain.initialize()

        summary = chain.get_conversation_summary()
        stats = chain.get_stats()

        return ApiResponse(
            data={
                "summary": summary,
                "stats": stats,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取摘要失败: {str(e)}")


@router.delete("/conversation/{conversation_id}/memory", response_model=ApiResponse[dict])
async def clear_conversation_memory(
    conversation_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    清空对话记忆
    
    清除指定对话的上下文记忆
    """
    try:
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

        chain.clear_context()

        return ApiResponse(
            data={
                "message": "对话记忆已清空",
                "conversation_id": conversation_id,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空记忆失败: {str(e)}")
