"""
对话管理 API 路由
"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantDep
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

router = APIRouter(prefix="/conversation", tags=["对话管理"])


@router.post("/create", response_model=ApiResponse[ConversationResponse])
async def create_conversation(
    conversation_data: ConversationCreate,
    tenant_id: TenantDep,
    db: DBDep,
):
    """创建会话"""
    service = ConversationService(db, tenant_id)
    conversation = await service.create_conversation(
        user_external_id=conversation_data.user_id,
        channel=conversation_data.channel,
    )
    return ApiResponse(data=conversation)


@router.get(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationDetailResponse],
)
async def get_conversation(
    conversation_id: str,
    tenant_id: TenantDep,
    db: DBDep,
):
    """获取会话详情"""
    service = ConversationService(db, tenant_id)
    conversation = await service.get_conversation(conversation_id)

    # 获取消息列表
    messages = await service.get_messages(conversation_id)

    # 获取用户信息
    user = await service.get_or_create_user(conversation.user.user_external_id)

    response = ConversationDetailResponse(
        **conversation.__dict__,
        messages=messages,
        user=user,
    )

    return ApiResponse(data=response)


@router.get("/list", response_model=ApiResponse[PaginatedResponse[ConversationResponse]])
async def list_conversations(
    tenant_id: TenantDep,
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


@router.post(
    "/{conversation_id}/messages",
    response_model=ApiResponse[MessageResponse],
)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    发送消息（同步方式）
    
    注：生产环境建议使用 WebSocket 接口实现流式返回
    """
    service = ConversationService(db, tenant_id)

    # 添加用户消息
    user_message = await service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=message_data.content,
    )

    # TODO: 调用 LLM 生成回复（这里先返回简单回复）
    assistant_content = "这是一个示例回复。实际应用中会调用 LLM 服务生成回复。"

    # 添加助手回复
    assistant_message = await service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_content,
    )

    return ApiResponse(data=assistant_message)


@router.put(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
)
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    tenant_id: TenantDep,
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
    tenant_id: TenantDep,
    db: DBDep,
    limit: int = Query(50, ge=1, le=200),
):
    """获取会话消息列表"""
    service = ConversationService(db, tenant_id)
    messages = await service.get_messages(conversation_id, limit=limit)
    return ApiResponse(data=messages)
