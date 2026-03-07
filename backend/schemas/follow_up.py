"""定时跟进 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


class FollowUpCreateRequest(BaseModel):
    user_id: int = Field(..., description="目标用户ID")
    rule_id: int | None = Field(None, description="关联规则ID")
    reason: str = Field(..., description="跟进原因")
    ai_context: dict | None = Field(None, description="AI上下文")
    total_steps: int = Field(3, ge=1, le=10, description="总步骤数")
    interval_days: int = Field(3, ge=1, le=30, description="跟进间隔(天)")


class FollowUpUpdateRequest(BaseModel):
    ai_context: dict | None = Field(None, description="AI上下文")
    total_steps: int | None = Field(None, ge=1, le=10, description="总步骤数")
    interval_days: int | None = Field(None, ge=1, le=30, description="跟进间隔(天)")


class FollowUpResponse(TimestampSchema):
    id: int
    tenant_id: str
    user_id: int
    rule_id: int | None = None
    reason: str
    ai_context: dict | None = None
    total_steps: int
    current_step: int
    next_follow_up_at: datetime | None = None
    interval_days: int
    status: str
    user_responded: int
    converted: int
    converted_order_id: int | None = None


class FollowUpDashboardResponse(BaseModel):
    active_plans: int = 0
    completed_plans: int = 0
    converted_plans: int = 0
    total_follow_ups_sent: int = 0
    conversion_rate: float = 0.0
