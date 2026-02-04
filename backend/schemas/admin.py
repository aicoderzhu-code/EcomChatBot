"""
管理员相关 Schema
"""
from datetime import datetime

from pydantic import EmailStr, Field

from schemas.base import BaseSchema, TimestampSchema


# ============ 管理员 Schema ============
class AdminBase(BaseSchema):
    """管理员基础 Schema"""

    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone: str | None = Field(None, max_length=20, description="手机号")
    role: str = Field(
        "viewer",
        pattern="^(super_admin|finance_admin|support_admin|viewer)$",
        description="角色",
    )


class AdminCreate(AdminBase):
    """创建管理员"""

    password: str = Field(..., min_length=8, max_length=64, description="密码")


class AdminUpdate(BaseSchema):
    """更新管理员"""

    email: EmailStr | None = None
    phone: str | None = None
    role: str | None = None
    status: str | None = None


class AdminResponse(AdminBase, TimestampSchema):
    """管理员响应"""

    id: int
    admin_id: str
    status: str
    last_login_at: datetime | None
    last_login_ip: str | None


# ============ 管理员登录 ============
class AdminLoginRequest(BaseSchema):
    """管理员登录请求"""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=64)


class AdminLoginResponse(BaseSchema):
    """管理员登录响应"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminResponse


# ============ 操作日志 Schema ============
class AdminOperationLogResponse(TimestampSchema):
    """操作日志响应"""

    id: int
    admin_id: str
    operation_type: str
    resource_type: str
    resource_id: str
    operation_details: dict | None
    before_value: dict | None
    after_value: dict | None
    ip_address: str | None
    status: str


# ============ 权限模板 Schema ============
class PermissionTemplateBase(BaseSchema):
    """权限模板基础 Schema"""

    template_name: str = Field(..., max_length=128, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    enabled_features: list[str] = Field(..., description="开通的功能模块")
    quota_config: dict = Field(..., description="配额配置")


class PermissionTemplateCreate(PermissionTemplateBase):
    """创建权限模板"""

    pass


class PermissionTemplateUpdate(BaseSchema):
    """更新权限模板"""

    template_name: str | None = None
    description: str | None = None
    enabled_features: list[str] | None = None
    quota_config: dict | None = None
    is_active: bool | None = None


class PermissionTemplateResponse(PermissionTemplateBase, TimestampSchema):
    """权限模板响应"""

    id: int
    template_id: str
    usage_count: int
    is_active: bool
    created_by: str | None


# ============ 批量操作 Schema ============
class BatchOperationRequest(BaseSchema):
    """批量操作请求"""

    tenant_ids: list[str] = Field(..., min_length=1, description="租户ID列表")
    operation: str = Field(..., description="操作类型")
    params: dict | None = Field(None, description="操作参数")


class BatchOperationResponse(BaseSchema):
    """批量操作响应"""

    success: list[str] = Field(default_factory=list, description="成功的租户ID")
    failed: list[dict] = Field(default_factory=list, description="失败的租户信息")
    total: int = Field(..., description="总数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
