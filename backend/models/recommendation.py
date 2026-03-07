"""增购推荐模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class RecommendRuleType(str, PyEnum):
    CROSS_SELL = "cross_sell"
    UPSELL = "upsell"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    REPLENISH = "replenish"


class RecommendTriggerType(str, PyEnum):
    IN_CONVERSATION = "in_conversation"
    POST_PURCHASE = "post_purchase"
    MANUAL = "manual"


class RecommendStrategy(str, PyEnum):
    MANUAL = "manual"
    AI_SIMILAR = "ai_similar"
    AI_COMPLEMENTARY = "ai_complementary"
    POPULAR_IN_CATEGORY = "popular_in_category"


class RecommendationRule(TenantBaseModel):
    """推荐规则表"""

    __tablename__ = "recommendation_rules"
    __table_args__ = (
        Index("idx_rec_rule_tenant", "tenant_id"),
        Index("idx_rec_rule_active", "is_active"),
        {"comment": "推荐规则表"},
    )

    name: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="规则名称"
    )
    rule_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="推荐类型(cross_sell/upsell/...)"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_conversation", comment="触发类型"
    )
    trigger_product_ids: Mapped[list | None] = mapped_column(
        JSONField, comment="触发商品ID列表(JSON)"
    )
    trigger_category: Mapped[str | None] = mapped_column(
        String(128), comment="触发商品分类"
    )
    trigger_conditions: Mapped[dict | None] = mapped_column(
        JSONField, comment="触发条件(JSON)"
    )
    recommend_product_ids: Mapped[list | None] = mapped_column(
        JSONField, comment="推荐商品ID列表(JSON)"
    )
    recommend_category: Mapped[str | None] = mapped_column(
        String(128), comment="推荐商品分类"
    )
    recommend_strategy: Mapped[str] = mapped_column(
        String(64), nullable=False, default="manual", comment="推荐策略"
    )
    max_recommendations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="最大推荐数"
    )
    ai_prompt: Mapped[str | None] = mapped_column(
        Text, comment="AI推荐提示词"
    )
    is_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="是否启用"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="优先级"
    )

    def __repr__(self) -> str:
        return f"<RecommendationRule {self.name} ({self.rule_type})>"


class RecommendationLog(TenantBaseModel):
    """推荐记录表"""

    __tablename__ = "recommendation_logs"
    __table_args__ = (
        Index("idx_rec_log_tenant", "tenant_id"),
        Index("idx_rec_log_user", "user_id"),
        {"comment": "推荐记录表"},
    )

    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="用户ID"
    )
    rule_id: Mapped[int | None] = mapped_column(
        Integer, comment="规则ID"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="触发类型"
    )
    trigger_product_id: Mapped[int | None] = mapped_column(
        Integer, comment="触发商品ID"
    )
    trigger_order_id: Mapped[int | None] = mapped_column(
        Integer, comment="触发订单ID"
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(256), comment="对话ID"
    )
    recommended_product_ids: Mapped[list | None] = mapped_column(
        JSONField, comment="推荐商品ID列表(JSON)"
    )
    recommendation_text: Mapped[str | None] = mapped_column(
        Text, comment="推荐文案"
    )
    displayed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否已展示"
    )
    clicked_product_id: Mapped[int | None] = mapped_column(
        Integer, comment="点击的商品ID"
    )
    converted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否已转化"
    )
    converted_order_id: Mapped[int | None] = mapped_column(
        Integer, comment="转化订单ID"
    )

    def __repr__(self) -> str:
        return f"<RecommendationLog user={self.user_id} rule={self.rule_id}>"
