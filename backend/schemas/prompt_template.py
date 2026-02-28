"""提示词模板 Schema"""
from pydantic import BaseModel, Field

from schemas.base import BaseSchema, TimestampSchema


class PromptTemplateCreate(BaseModel):
    """创建模板"""
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    template_type: str = Field(..., pattern="^(poster|video|title|description)$", description="模板类型")
    content: str = Field(..., min_length=1, description="模板内容")
    variables: list[str] | None = Field(None, description="变量列表")
    is_default: bool = Field(False, description="是否为默认模板")


class PromptTemplateUpdate(BaseModel):
    """更新模板"""
    name: str | None = Field(None, min_length=1, max_length=128)
    content: str | None = Field(None, min_length=1)
    variables: list[str] | None = None
    is_default: bool | None = None


class PromptTemplateResponse(TimestampSchema):
    """模板响应"""
    id: int
    tenant_id: str
    name: str
    template_type: str
    content: str
    variables: list[str] | None = None
    is_default: bool
    usage_count: int
