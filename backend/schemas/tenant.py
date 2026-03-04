"""
租户相关 Schema
"""
from datetime import datetime
import json
import re

from pydantic import EmailStr, Field, field_validator

from schemas.base import BaseSchema, TimestampSchema


# ============ 租户 Schema ============
class TenantBase(BaseSchema):
    """租户基础 Schema"""

    company_name: str = Field(..., min_length=1, max_length=256, description="公司名称")
    contact_name: str | None = Field(None, max_length=128, description="联系人姓名")
    contact_email: EmailStr = Field(..., description="联系邮箱")
    contact_phone: str | None = Field(None, max_length=20, description="联系电话")


class TenantCreate(TenantBase):
    """创建租户"""

    password: str = Field(..., min_length=8, max_length=64, description="初始密码")
    initial_plan: str = Field("free", description="初始套餐")


class TenantUpdate(BaseSchema):
    """更新租户"""

    company_name: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    config: dict | None = None
    remarks: str | None = None


class TenantUpdateStatus(BaseSchema):
    """更新租户状态"""

    status: str = Field(..., pattern="^(active|suspended|deleted)$", description="状态")
    reason: str | None = Field(None, description="原因")


class TenantResponse(TenantBase, TimestampSchema):
    """租户响应"""

    id: int
    tenant_id: str
    status: str
    current_plan: str
    plan_expire_at: datetime | None
    total_conversations: int
    total_messages: int
    total_spent: float
    last_active_at: datetime | None
    api_key_prefix: str | None


class TenantWithAPIKey(TenantResponse):
    """租户响应（包含 API Key）"""

    api_key: str = Field(..., description="API Key（仅创建时返回一次）")


# ============ 订阅 Schema ============
class SubscriptionBase(BaseSchema):
    """订阅基础 Schema"""

    plan_type: str = Field(..., description="套餐类型")


class SubscriptionCreate(SubscriptionBase):
    """创建订阅"""

    tenant_id: str
    duration_months: int = Field(1, ge=1, le=36, description="订阅时长（月）")
    auto_renew: bool = Field(False, description="是否自动续费")


class SubscriptionUpdate(BaseSchema):
    """更新订阅"""

    plan_type: str | None = None
    auto_renew: bool | None = None


class SubscriptionResponse(SubscriptionBase, TimestampSchema):
    """订阅响应"""

    id: int
    tenant_id: str
    status: str
    enabled_features: list[str]
    start_date: datetime
    expire_at: datetime
    is_trial: bool

    @field_validator('enabled_features', mode='before')
    @classmethod
    def parse_enabled_features(cls, v):
        """将JSON字符串转换为list"""
        if isinstance(v, str):
            return json.loads(v)
        return v


# ============ 账单 Schema ============
class BillResponse(TimestampSchema):
    """账单响应"""

    id: int
    bill_id: str
    tenant_id: str
    billing_period: str
    base_fee: float
    discount: float
    adjustment_amount: float
    total_amount: float
    status: str
    payment_method: str | None
    payment_time: datetime | None
    due_date: datetime


# ============ 租户注册 ============
class TenantRegisterRequest(BaseSchema):
    """租户注册请求"""

    company_name: str = Field(..., min_length=1, max_length=256)
    contact_name: str = Field(..., min_length=1, max_length=128)
    contact_email: EmailStr
    contact_phone: str | None = None
    password: str = Field(..., min_length=8, max_length=64, description="密码")

    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码须包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码须包含至少一个小写字母')
        if not re.search(r'\d', v):
            raise ValueError('密码须包含至少一个数字')
        return v


class TenantRegisterResponse(BaseSchema):
    """租户注册响应"""

    tenant_id: str
    api_key: str
    message: str = "注册成功"


class ResetApiKeyResponse(BaseSchema):
    """重置 API Key 响应"""

    api_key: str = Field(..., description="新的 API Key（明文，仅此一次）")
    api_key_prefix: str = Field(..., description="API Key 前缀")
    message: str = "API Key 已重置，请妥善保存"


# ============ 租户认证 ============
class TenantLoginRequest(BaseSchema):
    """租户登录请求"""

    email: EmailStr
    password: str


class TenantLoginResponse(BaseSchema):
    """租户登录响应"""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    tenant_id: str


# ============ Token 刷新 ============
class TokenRefreshRequest(BaseSchema):
    """刷新 Token 请求"""

    refresh_token: str = Field(..., description="刷新 Token")


class TokenRefreshResponse(BaseSchema):
    """刷新 Token 响应"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============ 登出 ============
class TenantLogoutRequest(BaseSchema):
    """登出请求"""

    refresh_token: str | None = Field(None, description="刷新 Token（可选）")


class TenantLogoutResponse(BaseSchema):
    """登出响应"""

    message: str = "登出成功"
