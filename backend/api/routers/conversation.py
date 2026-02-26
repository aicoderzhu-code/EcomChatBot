"""
对话管理 API 路由
"""
import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.dependencies import DBDep, TenantDep, TenantFlexDep
from api.middleware import ConcurrentQuotaDep, ConversationQuotaDep
from schemas import (
    ApiResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    PaginatedResponse,
)
from services import ConversationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["对话管理"])


@router.post("/create", response_model=ApiResponse[ConversationResponse])
async def create_conversation(
    conversation_data: ConversationCreate,
    tenant_id: ConcurrentQuotaDep,  # 检查并发会话配额
    db: DBDep,
):
    """
    创建会话

    - **user_id**: 用户ID
    - **channel**: 渠道(web/app等)
    - **metadata**: 元数据(可选)

    ⚠️ 会检查并发会话数配额
    """
    service = ConversationService(db, tenant_id)
    conversation = await service.create_conversation(
        user_external_id=conversation_data.user_id,
        channel=conversation_data.channel,
    )
    return ApiResponse(data=conversation)


@router.get("/list", response_model=ApiResponse[PaginatedResponse[ConversationResponse]])
async def list_conversations(
    tenant_id: TenantFlexDep,
    db: DBDep,
    user_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询会话列表"""
    service = ConversationService(db, tenant_id)
    conversations, total = await service.list_conversations(
        user_external_id=user_id,
        status=status,
        page=page,
        size=size,
    )

    paginated = PaginatedResponse.create(
        items=conversations,
        total=total,
        page=page,
        size=size,
    )

    return ApiResponse(data=paginated)


@router.get(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationDetailResponse],
)
async def get_conversation(
    conversation_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取会话详情"""
    service = ConversationService(db, tenant_id)
    conversation = await service.get_conversation(conversation_id)

    messages = await service.get_messages(conversation_id)

    # user already loaded via selectinload in get_conversation
    user = conversation.user

    conv_dict = {k: v for k, v in conversation.__dict__.items() if not k.startswith('_')}
    conv_dict.pop('messages', None)
    conv_dict.pop('user', None)

    response = ConversationDetailResponse(
        **conv_dict,
        messages=messages,
        user=user,
    )

    return ApiResponse(data=response)


@router.post(
    "/{conversation_id}/messages",
    response_model=ApiResponse[MessageResponse],
)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    tenant_id: ConversationQuotaDep,  # 检查对话次数配额
    db: DBDep,
):
    """
    发送消息（同步方式）

    注：生产环境建议使用 WebSocket 或 SSE 流式接口

    ⚠️ 会检查对话次数配额
    """
    from services import ConversationChainService

    service = ConversationService(db, tenant_id)

    await service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=message_data.content,
    )

    try:
        chain = ConversationChainService(
            db=db, tenant_id=tenant_id, conversation_id=conversation_id,
        )
        await chain.initialize()
        result = await chain.chat(user_input=message_data.content)
        assistant_content = result["response"]
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
    except Exception as e:
        logger.error("LLM generation failed for conversation %s: %s", conversation_id, e)
        assistant_content = "抱歉，我遇到了一些问题，请稍后再试。"
        input_tokens = 0
        output_tokens = 0

    assistant_message = await service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return ApiResponse(data=assistant_message)


@router.put(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
)
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新会话（关闭会话、评价等）"""
    service = ConversationService(db, tenant_id)

    if conversation_data.status == "closed":
        conversation = await service.close_conversation(
            conversation_id=conversation_id,
            satisfaction_score=conversation_data.satisfaction_score,
            feedback=conversation_data.feedback,
        )
    else:
        conversation = await service.get_conversation(conversation_id)

    return ApiResponse(data=conversation)


@router.get(
    "/{conversation_id}/messages",
    response_model=ApiResponse[list[MessageResponse]],
)
async def get_messages(
    conversation_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
    limit: int = Query(50, ge=1, le=200),
):
    """获取会话消息列表"""
    service = ConversationService(db, tenant_id)
    messages = await service.get_messages(conversation_id, limit=limit)
    return ApiResponse(data=messages)


class TakeoverRequest(BaseModel):
    reason: str | None = None


@router.put(
    "/{conversation_id}/takeover",
    response_model=ApiResponse[ConversationResponse],
)
async def takeover_conversation(
    conversation_id: str,
    data: TakeoverRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """人工接管会话"""
    service = ConversationService(db, tenant_id)
    conversation = await service.get_conversation(conversation_id)
    conversation.status = "waiting"
    conversation.transferred_to_human = True
    if data.reason:
        conversation.transfer_reason = data.reason
    await db.commit()
    await db.refresh(conversation)
    return ApiResponse(data=conversation)
