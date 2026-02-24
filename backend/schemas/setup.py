"""
系统初始化相关 Schema
"""
import re

from pydantic import EmailStr, Field, field_validator

from schemas.base import BaseSchema


class SetupStatus(BaseSchema):
    """系统初始化状态"""

    initialized: bool = Field(..., description="系统是否已初始化")
    admin_count: int = Field(..., description="管理员数量")


class InitialAdminCreate(BaseSchema):
    """创建初始超级管理员"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="用户名 (3-64字符)"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="密码 (至少8位，包含大小写字母和数字)"
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="确认密码"
    )
    email: EmailStr = Field(..., description="邮箱")
    phone: str | None = Field(None, max_length=20, description="手机号")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度至少为8个字符")

        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")

        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")

        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")

        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        """验证确认密码"""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名"""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError("用户名必须以字母开头，只能包含字母、数字和下划线")
        return v
