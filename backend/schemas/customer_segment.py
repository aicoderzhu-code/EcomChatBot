"""客户分群 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


# ===== Request Schemas =====

class SegmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="分群名称")
    description: str | None = Field(None, description="分群描述")
    segment_type: str = Field("manual", pattern="^(manual|dynamic)$", description="分群类型")
    filter_rules: dict | None = Field(None, description="动态分群筛选条件")
    is_active: int = Field(1, description="是否启用")


class SegmentUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128, description="分群名称")
    description: str | None = Field(None, description="分群描述")
    filter_rules: dict | None = Field(None, description="动态分群筛选条件")
    is_active: int | None = Field(None, description="是否启用")


class SegmentPreviewRequest(BaseModel):
    filter_rules: dict = Field(..., description="筛选条件")


class SegmentAddMembersRequest(BaseModel):
    user_ids: list[int] = Field(..., description="用户ID列表")


# ===== Response Schemas =====

class SegmentResponse(TimestampSchema):
    id: int
    tenant_id: str
    name: str
    description: str | None = None
    segment_type: str
    filter_rules: dict | None = None
    member_count: int
    last_refreshed_at: datetime | None = None
    is_active: int


class SegmentMemberResponse(BaseModel):
    id: int
    user_id: int
    nickname: str | None = None
    vip_level: int = 0
    total_conversations: int = 0
    added_at: datetime | None = None

    model_config = {"from_attributes": True}


class SegmentPreviewResponse(BaseModel):
    matched_count: int
    sample_users: list[dict] = []
