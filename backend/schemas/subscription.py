"""
订阅相关 Pydantic schemas
"""
import json
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ========== 订阅请求 Schemas ==========

class SubscribePlanRequest(BaseModel):
    """订阅套餐请求"""
    plan_type: str = Field(..., description="套餐类型: trial/monthly/quarterly/semi_annual/annual")
    duration_months: int = Field(..., ge=1, le=36, description="订阅时长（月）: 1-36")
    payment_method: str = Field(default="alipay", description="支付方式: alipay")
    auto_renew: bool = Field(default=False, description="是否自动续费")


class ChangePlanRequest(BaseModel):
    """变更套餐请求"""
    new_plan_type: str = Field(..., description="新套餐类型: monthly/quarterly/semi_annual/annual")
    effective_immediately: bool = Field(default=True, description="是否立即生效")


# ========== 订阅响应 Schemas ==========

class SubscriptionDetail(BaseModel):
    """订阅详情响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    plan_type: str
    status: str
    start_date: datetime
    expire_at: datetime
    auto_renew: bool
    is_trial: bool

    # 功能信息
    enabled_features: List[str]

    @field_validator('enabled_features', mode='before')
    @classmethod
    def parse_enabled_features(cls, v):
        """将JSON字符串转换为list"""
        if isinstance(v, str):
            return json.loads(v)
        return v

    # 待变更套餐（如果有）
    pending_plan: Optional[str] = None
    plan_change_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


class ProratedPriceDetail(BaseModel):
    """差价计算详情"""
    current_plan: str = Field(..., description="当前套餐")
    new_plan: str = Field(..., description="新套餐")
    current_plan_value: Decimal = Field(..., description="当前套餐剩余价值（元）")
    new_plan_value: Decimal = Field(..., description="新套餐剩余价值（元）")
    prorated_charge: Decimal = Field(..., description="需补差价（元）")
    remaining_days: int = Field(..., description="剩余天数")


class SubscriptionResponse(BaseModel):
    """订阅操作响应"""
    success: bool
    message: str
    subscription: Optional[SubscriptionDetail] = None
    order_number: Optional[str] = None  # 如果需要支付，返回订单号
    payment_required: bool = False  # 是否需要支付
    payment_amount: Optional[Decimal] = None  # 需要支付的金额
