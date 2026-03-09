"""
对话相关 Schema
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from schemas.base import BaseSchema, TimestampSchema


# ============ 用户 Schema ============
class UserBase(BaseSchema):
    """用户基础 Schema"""

    user_external_id: str = Field(..., max_length=128, description="用户外部ID")
    nickname: str | None = Field(None, max_length=128, description="昵称")
    phone: str | None = Field(None, max_length=20, description="手机号")
    email: str | None = Field(None, max_length=128, description="邮箱")
    avatar: str | None = Field(None, max_length=512, description="头像URL")
    vip_level: int = Field(0, ge=0, description="VIP等级")


class UserCreate(UserBase):
    """创建用户"""

    pass


class UserUpdate(BaseSchema):
    """更新用户"""

    nickname: str | None = None
    phone: str | None = None
    email: str | None = None
    avatar: str | None = None
    vip_level: int | None = None
    profile: dict | None = None


class UserResponse(UserBase, TimestampSchema):
    """用户响应"""

    id: int
    tenant_id: str
    total_conversations: int
    last_conversation_at: datetime | None


# ============ 消息 Schema ============
class MessageCreate(BaseSchema):
    """创建消息（发送消息）"""

    content: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    attachments: list[dict] | None = Field(None, description="附件")


class MessageResponse(TimestampSchema):
    """消息响应"""

    id: int
    message_id: str
    conversation_id: str
    role: str
    content: str
    intent: str | None
    intent_confidence: float | None
    entities: dict | None
    response_time: int | None
    input_tokens: int | None
    output_tokens: int | None


# ============ 会话 Schema ============
class ConversationCreate(BaseSchema):
    """创建会话"""

    user_id: str = Field(..., description="用户外部ID")
    channel: str = Field("web", description="渠道")


class ConversationUpdate(BaseSchema):
    """更新会话"""

    status: str | None = Field(None, pattern="^(active|waiting|closed)$", description="状态")
    satisfaction_score: int | None = Field(None, ge=1, le=5, description="满意度评分")
    feedback: str | None = Field(None, description="用户反馈")


class ConversationResponse(TimestampSchema):
    """会话响应"""

    id: int
    conversation_id: str
    tenant_id: str
    user_id: int
    channel: str
    status: str
    start_time: datetime
    end_time: datetime | None
    satisfaction_score: int | None
    message_count: int
    token_usage: int
    primary_intent: str | None = None
    intent_distribution: dict | None = None
    summary: str | None = None


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（包含消息列表）"""

    messages: list[MessageResponse]
    user: UserResponse


# ============ WebSocket 消息格式 ============
class WebSocketMessage(BaseSchema):
    """WebSocket 消息格式"""

    type: str = Field(..., description="消息类型")
    data: dict = Field(..., description="消息数据")


class WebSocketClientMessage(BaseSchema):
    """客户端发送的 WebSocket 消息"""

    conversation_id: str
    message: str
    attachments: list[dict] | None = None


class WebSocketServerMessage(BaseSchema):
    """服务端发送的 WebSocket 消息"""

    type: str  # stream / complete / error
    content: str | None = None
    message_id: str | None = None
    error: str | None = None
