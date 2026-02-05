"""
Webhook相关的Pydantic模型
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class WebhookCreateRequest(BaseModel):
    """创建Webhook配置请求"""
    name: str = Field(..., min_length=1, max_length=128, description="配置名称")
    endpoint_url: str = Field(..., max_length=512, description="Webhook URL")
    events: list[str] = Field(..., min_length=1, description="监听的事件列表")
    secret: str | None = Field(None, max_length=128, description="签名密钥（可选，不提供则自动生成）")


class WebhookUpdateRequest(BaseModel):
    """更新Webhook配置请求"""
    name: str | None = Field(None, min_length=1, max_length=128, description="配置名称")
    endpoint_url: str | None = Field(None, max_length=512, description="Webhook URL")
    events: list[str] | None = Field(None, min_length=1, description="监听的事件列表")
    is_active: bool | None = Field(None, description="是否激活")


class WebhookResponse(BaseModel):
    """Webhook配置响应"""
    id: int
    tenant_id: str
    name: str
    endpoint_url: str
    events: list[str]
    is_active: bool
    total_calls: int
    success_calls: int
    failed_calls: int
    last_called_at: datetime | None
    last_status: str | None
    created_at: datetime
    updated_at: datetime

    # 不返回secret给前端
    model_config = {"from_attributes": True}


class WebhookLogResponse(BaseModel):
    """Webhook日志响应"""
    id: int
    webhook_config_id: int
    event_type: str
    event_id: str
    request_payload: dict
    response_status: int | None
    response_body: str | None
    status: str
    retry_count: int
    error_message: str | None
    processed_at: datetime | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
