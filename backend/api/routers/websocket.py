"""
WebSocket 实时对话路由
"""
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationException
from core.security import verify_api_key
from db.session import get_db
from services import (
    ConversationChainService,
    ConversationService,
    UsageService,
)
from services.knowledge_service import KnowledgeService
from services.websocket_service import connection_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def verify_websocket_auth(api_key: str, db: AsyncSession) -> str:
    """
    WebSocket 认证
    
    Args:
        api_key: API Key
        db: 数据库会话
        
    Returns:
        tenant_id
        
    Raises:
        AuthenticationException: 认证失败
    """
    tenant = await verify_api_key(db, api_key)
    if not tenant or not tenant.is_active:
        raise AuthenticationException("认证失败或租户未激活")

    return tenant.tenant_id


@router.websocket("/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    api_key: str = Query(..., description="API Key"),
    conversation_id: str = Query(..., description="会话 ID"),
):
    """
    WebSocket 实时对话端点
    
    连接 URL: ws://localhost:8000/api/v1/ws/chat?api_key=xxx&conversation_id=xxx
    
    消息格式（客户端发送）：
    {
        "type": "message",
        "content": "用户消息内容",
        "use_rag": false  // 是否使用 RAG
    }
    
    消息格式（服务端发送）：
    {
        "type": "message",  // 或 "stream" / "system" / "error"
        "role": "assistant",
        "content": "AI 回复内容",
        "timestamp": "2024-01-01T00:00:00"
    }
    """
    # 获取数据库会话
    db = None
    tenant_id = None

    try:
        # 认证
        async for session in get_db():
            db = session
            tenant_id = await verify_websocket_auth(api_key, db)
            break

        if not tenant_id or not db:
            await websocket.close(code=1008, reason="认证失败")
            return

        # 连接
        await connection_manager.connect(websocket, tenant_id, conversation_id)

        print(
            f"✓ WebSocket 连接建立: tenant={tenant_id}, conversation={conversation_id}"
        )

        # 初始化对话链
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        await chain.initialize()

        # 主消息循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message_data = json.loads(data)

                message_type = message_data.get("type", "message")
                user_input = message_data.get("content", "")
                use_rag = message_data.get("use_rag", False)

                if not user_input:
                    await connection_manager.send_error(
                        tenant_id, conversation_id, "消息内容不能为空"
                    )
                    continue

                # 处理不同类型的消息
                if message_type == "message":
                    await handle_chat_message(
                        db=db,
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        user_input=user_input,
                        use_rag=use_rag,
                        chain=chain,
                    )

                elif message_type == "ping":
                    # 心跳响应
                    await connection_manager.send_message(
                        tenant_id,
                        conversation_id,
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                    )

                else:
                    await connection_manager.send_error(
                        tenant_id, conversation_id, f"不支持的消息类型: {message_type}"
                    )

            except WebSocketDisconnect:
                print(f"✗ WebSocket 断开: tenant={tenant_id}, conversation={conversation_id}")
                break

            except json.JSONDecodeError:
                await connection_manager.send_error(
                    tenant_id, conversation_id, "消息格式错误，请发送有效的 JSON"
                )

            except Exception as e:
                print(f"处理消息错误: {e}")
                await connection_manager.send_error(
                    tenant_id, conversation_id, f"处理失败: {str(e)}"
                )

    except AuthenticationException as e:
        await websocket.close(code=1008, reason=str(e))
        return

    except Exception as e:
        print(f"WebSocket 错误: {e}")
        await websocket.close(code=1011, reason="服务器内部错误")

    finally:
        # 清理连接
        if tenant_id and conversation_id:
            connection_manager.disconnect(tenant_id, conversation_id)


async def handle_chat_message(
    db: AsyncSession,
    tenant_id: str,
    conversation_id: str,
    user_input: str,
    use_rag: bool,
    chain: ConversationChainService,
) -> None:
    """
    处理聊天消息
    
    Args:
        db: 数据库会话
        tenant_id: 租户 ID
        conversation_id: 会话 ID
        user_input: 用户输入
        use_rag: 是否使用 RAG
        chain: 对话链服务
    """
    try:
        # 1. 保存用户消息
        conversation_service = ConversationService(db, tenant_id)
        user_message = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_input,
        )

        # 2. 生成回复
        knowledge_items = None
        if use_rag:
            # 检索知识库
            knowledge_service = KnowledgeService(db, tenant_id)
            knowledge_list = await knowledge_service.search_knowledge(
                query=user_input,
                top_k=3,
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

            # 使用 RAG 对话
            result = await chain.chat_with_rag(
                user_input=user_input,
                knowledge_items=knowledge_items,
            )
        else:
            # 普通对话
            result = await chain.chat(user_input=user_input)

        # 4. 保存 AI 回复
        ai_message = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result["response"],
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
        )

        # 5. 记录用量
        usage_service = UsageService(db, tenant_id)
        await usage_service.record_conversation_usage(
            conversation_id=conversation_id,
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
        )

        # 6. 发送回复
        await connection_manager.send_text_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            content=result["response"],
            role="assistant",
        )

        # 7. 发送元数据
        await connection_manager.send_message(
            tenant_id,
            conversation_id,
            {
                "type": "metadata",
                "tokens": {
                    "input": result.get("input_tokens", 0),
                    "output": result.get("output_tokens", 0),
                    "total": result.get("total_tokens", 0),
                },
                "model": result.get("model"),
                "used_rag": use_rag,
                "sources": result.get("sources", []) if use_rag else None,
            },
        )

    except QuotaExceededException as e:
        await connection_manager.send_error(
            tenant_id, conversation_id, str(e), "QUOTA_EXCEEDED"
        )

    except Exception as e:
        print(f"处理对话消息错误: {e}")
        import traceback

        traceback.print_exc()
        await connection_manager.send_error(tenant_id, conversation_id, f"处理失败: {str(e)}")


@router.websocket("/chat/stream")
async def websocket_chat_stream_endpoint(
    websocket: WebSocket,
    api_key: str = Query(..., description="API Key"),
    conversation_id: str = Query(..., description="会话 ID"),
):
    """
    WebSocket 流式对话端点
    
    支持流式输出，逐字返回 AI 回复
    
    连接 URL: ws://localhost:8000/api/v1/ws/chat/stream?api_key=xxx&conversation_id=xxx
    """
    db = None
    tenant_id = None

    try:
        # 认证
        async for session in get_db():
            db = session
            tenant_id = await verify_websocket_auth(api_key, db)
            break

        if not tenant_id or not db:
            await websocket.close(code=1008, reason="认证失败")
            return

        # 连接
        await connection_manager.connect(websocket, tenant_id, conversation_id)

        # 初始化对话链
        chain = ConversationChainService(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        await chain.initialize()

        # 获取流式 LLM
        streaming_llm = chain.llm_service.get_streaming_llm()

        # 主消息循环
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                user_input = message_data.get("content", "")
                if not user_input:
                    continue

                # 保存用户消息
                conversation_service = ConversationService(db, tenant_id)
                await conversation_service.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_input,
                )

                # 获取系统提示词
                from services.prompt_service import PromptService

                prompt_service = PromptService()
                system_prompt = prompt_service.get_system_prompt()

                # 获取对话历史
                chat_history = chain.memory.get_chat_history()
                messages = chat_history.copy()
                messages.append({"role": "user", "content": user_input})

                # 流式生成（简化版）
                # TODO: 实现真正的流式输出
                from langchain.schema import HumanMessage, SystemMessage

                lc_messages = [SystemMessage(content=system_prompt)]
                for msg in messages:
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))

                response = await streaming_llm.ainvoke(lc_messages)
                response_text = response.content

                # 模拟流式输出（按字符发送）
                for i, char in enumerate(response_text):
                    await connection_manager.send_streaming_chunk(
                        tenant_id,
                        conversation_id,
                        char,
                        is_final=(i == len(response_text) - 1),
                    )

                # 保存 AI 回复
                await conversation_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response_text,
                )

                # 更新记忆
                chain.memory.add_user_message(user_input)
                chain.memory.add_ai_message(response_text)

            except WebSocketDisconnect:
                break

            except Exception as e:
                print(f"流式对话错误: {e}")
                await connection_manager.send_error(tenant_id, conversation_id, str(e))

    except Exception as e:
        print(f"WebSocket 流式连接错误: {e}")
        await websocket.close(code=1011, reason="服务器内部错误")

    finally:
        if tenant_id and conversation_id:
            connection_manager.disconnect(tenant_id, conversation_id)


@router.get("/connections/stats")
async def get_websocket_stats():
    """
    获取 WebSocket 连接统计
    
    管理接口，无需认证
    """
    stats = connection_manager.get_stats()
    return {"success": True, "data": stats}
