"""
平台对接 Pydantic Schemas
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PinduoduoWebhookPayload(BaseModel):
    """拼多多 Webhook 消息体"""
    shop_id: str | int
    buyer_id: str | int
    conversation_id: str | int
    content: str = ""
    msg_type: int = 1
    extra: dict[str, Any] | None = None


class PlatformConfigCreate(BaseModel):
    """创建/更新平台配置"""
    app_key: str = Field(..., description="平台 App Key")
    app_secret: str = Field(..., description="平台 App Secret")
    auto_reply_threshold: float = Field(0.7, ge=0.0, le=1.0, description="自动回复置信度阈值")
    human_takeover_message: str | None = Field(None, description="转人工提示语")


class PlatformConfigResponse(BaseModel):
    """平台配置响应"""
    id: int
    tenant_id: str
    platform_type: str
    app_key: str
    shop_id: str | None
    shop_name: str | None
    is_active: bool
    auto_reply_threshold: float
    human_takeover_message: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
