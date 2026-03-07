"""增购推荐 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


class RecommendationRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="规则名称")
    rule_type: str = Field(..., description="推荐类型")
    trigger_type: str = Field("in_conversation", description="触发类型")
    trigger_product_ids: list[int] | None = Field(None, description="触发商品ID列表")
    trigger_category: str | None = Field(None, description="触发商品分类")
    trigger_conditions: dict | None = Field(None, description="触发条件")
    recommend_product_ids: list[int] | None = Field(None, description="推荐商品ID列表")
    recommend_category: str | None = Field(None, description="推荐商品分类")
    recommend_strategy: str = Field("manual", description="推荐策略")
    max_recommendations: int = Field(3, ge=1, le=10, description="最大推荐数")
    ai_prompt: str | None = Field(None, description="AI推荐提示词")
    priority: int = Field(0, description="优先级")


class RecommendationRuleUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256, description="规则名称")
    trigger_product_ids: list[int] | None = Field(None, description="触发商品ID列表")
    trigger_category: str | None = Field(None, description="触发商品分类")
    trigger_conditions: dict | None = Field(None, description="触发条件")
    recommend_product_ids: list[int] | None = Field(None, description="推荐商品ID列表")
    recommend_category: str | None = Field(None, description="推荐商品分类")
    recommend_strategy: str | None = Field(None, description="推荐策略")
    max_recommendations: int | None = Field(None, ge=1, le=10, description="最大推荐数")
    ai_prompt: str | None = Field(None, description="AI推荐提示词")
    priority: int | None = Field(None, description="优先级")


class RecommendationRuleResponse(TimestampSchema):
    id: int
    tenant_id: str
    name: str
    rule_type: str
    trigger_type: str
    trigger_product_ids: list[int] | None = None
    trigger_category: str | None = None
    trigger_conditions: dict | None = None
    recommend_product_ids: list[int] | None = None
    recommend_category: str | None = None
    recommend_strategy: str
    max_recommendations: int
    ai_prompt: str | None = None
    is_active: int
    priority: int


class RecommendationLogResponse(TimestampSchema):
    id: int
    tenant_id: str
    user_id: int
    rule_id: int | None = None
    trigger_type: str
    trigger_product_id: int | None = None
    trigger_order_id: int | None = None
    conversation_id: str | None = None
    recommended_product_ids: list[int] | None = None
    recommendation_text: str | None = None
    displayed: int
    clicked_product_id: int | None = None
    converted: int
    converted_order_id: int | None = None


class RecommendationPreviewRequest(BaseModel):
    rule_id: int | None = Field(None, description="规则ID")
    user_id: int | None = Field(None, description="用户ID")
    product_id: int | None = Field(None, description="商品ID")


class RecommendationStatsResponse(BaseModel):
    total_recommendations: int = 0
    total_displayed: int = 0
    total_clicked: int = 0
    total_converted: int = 0
    click_rate: float = 0.0
    conversion_rate: float = 0.0
