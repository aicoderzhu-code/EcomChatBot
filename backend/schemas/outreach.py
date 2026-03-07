"""外呼活动 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


# ===== Campaign Schemas =====

class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="活动名称")
    campaign_type: str = Field("manual", description="活动类型")
    segment_id: int | None = Field(None, description="分群ID")
    content_strategy: str = Field("template", pattern="^(template|ai_generated)$", description="内容策略")
    content_template: str | None = Field(None, description="消息模板")
    ai_prompt: str | None = Field(None, description="AI生成提示词")
    channel: str = Field("platform_message", description="发送渠道")
    platform_type: str | None = Field(None, description="平台类型")
    platform_config_id: int | None = Field(None, description="平台配置ID")
    scheduled_at: datetime | None = Field(None, description="计划发送时间")
    max_per_user_per_day: int = Field(3, ge=1, le=10, description="每人每天最大触达次数")
    cooldown_hours: int = Field(24, ge=1, description="冷却时间(小时)")


class CampaignUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256, description="活动名称")
    segment_id: int | None = Field(None, description="分群ID")
    content_strategy: str | None = Field(None, description="内容策略")
    content_template: str | None = Field(None, description="消息模板")
    ai_prompt: str | None = Field(None, description="AI生成提示词")
    platform_type: str | None = Field(None, description="平台类型")
    platform_config_id: int | None = Field(None, description="平台配置ID")
    scheduled_at: datetime | None = Field(None, description="计划发送时间")
    max_per_user_per_day: int | None = Field(None, ge=1, le=10, description="每人每天最大触达次数")
    cooldown_hours: int | None = Field(None, ge=1, description="冷却时间(小时)")


class CampaignResponse(TimestampSchema):
    id: int
    tenant_id: str
    name: str
    campaign_type: str
    segment_id: int | None = None
    rule_id: int | None = None
    content_strategy: str
    content_template: str | None = None
    ai_prompt: str | None = None
    channel: str | None = None
    platform_type: str | None = None
    platform_config_id: int | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str
    total_targets: int
    sent_count: int
    delivered_count: int
    failed_count: int
    clicked_count: int
    converted_count: int
    max_per_user_per_day: int
    cooldown_hours: int


class CampaignStatsResponse(BaseModel):
    total_targets: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    failed_count: int = 0
    clicked_count: int = 0
    converted_count: int = 0
    send_rate: float = 0.0
    delivery_rate: float = 0.0
    conversion_rate: float = 0.0


# ===== OutreachTask Schemas =====

class OutreachTaskResponse(TimestampSchema):
    id: int
    tenant_id: str
    campaign_id: int | None = None
    rule_id: int | None = None
    user_id: int
    content: str | None = None
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    converted_at: datetime | None = None
    error_message: str | None = None
    follow_up_plan_id: int | None = None
    follow_up_sequence: int | None = None


# ===== Rule Schemas =====

class RuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="规则名称")
    rule_type: str = Field(..., description="规则类型")
    trigger_conditions: dict | None = Field(None, description="触发条件")
    content_strategy: str = Field("template", description="内容策略")
    content_template: str | None = Field(None, description="消息模板")
    ai_prompt: str | None = Field(None, description="AI生成提示词")
    channel: str = Field("platform_message", description="发送渠道")
    platform_type: str | None = Field(None, description="平台类型")
    platform_config_id: int | None = Field(None, description="平台配置ID")
    max_triggers_per_user: int = Field(1, ge=1, description="每用户最大触发次数")
    cooldown_hours: int = Field(72, ge=1, description="冷却时间(小时)")


class RuleUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256, description="规则名称")
    trigger_conditions: dict | None = Field(None, description="触发条件")
    content_strategy: str | None = Field(None, description="内容策略")
    content_template: str | None = Field(None, description="消息模板")
    ai_prompt: str | None = Field(None, description="AI生成提示词")
    platform_type: str | None = Field(None, description="平台类型")
    platform_config_id: int | None = Field(None, description="平台配置ID")
    max_triggers_per_user: int | None = Field(None, ge=1, description="每用户最大触发次数")
    cooldown_hours: int | None = Field(None, ge=1, description="冷却时间(小时)")


class RuleResponse(TimestampSchema):
    id: int
    tenant_id: str
    name: str
    rule_type: str
    trigger_conditions: dict | None = None
    content_strategy: str
    content_template: str | None = None
    ai_prompt: str | None = None
    channel: str | None = None
    platform_type: str | None = None
    platform_config_id: int | None = None
    is_active: int
    max_triggers_per_user: int
    cooldown_hours: int
    total_triggered: int
    total_converted: int
