"""内容模板 Schema"""
from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


class ContentTemplateResponse(TimestampSchema):
    """内容模板响应"""
    id: int
    tenant_id: str | None = None
    name: str
    category: str
    scene_type: str
    prompt_template: str
    variables: list[dict] | None = None
    style_options: list[str] | None = None
    platform_presets: dict | None = None
    default_params: dict | None = None
    thumbnail_url: str | None = None
    is_system: bool
    is_active: bool
    sort_order: int
    usage_count: int


class ContentTemplateCreate(BaseModel):
    """创建内容模板"""
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    category: str = Field(..., pattern="^(poster|video)$", description="模板类别")
    scene_type: str = Field(..., min_length=1, max_length=64, description="场景类型")
    prompt_template: str = Field(..., min_length=1, description="提示词模板")
    variables: list[dict] | None = Field(None, description="变量定义")
    style_options: list[str] | None = Field(None, description="风格选项")
    platform_presets: dict | None = Field(None, description="平台预设参数")
    default_params: dict | None = Field(None, description="默认生成参数")
    thumbnail_url: str | None = Field(None, description="缩略图URL")


class TemplateRenderRequest(BaseModel):
    """模板渲染请求"""
    product_id: int | None = Field(None, description="商品ID")
    overrides: dict | None = Field(None, description="用户自定义变量值")
    target_platform: str | None = Field(None, description="目标平台")


class TemplateRenderResponse(BaseModel):
    """模板渲染响应"""
    rendered_prompt: str = Field(..., description="渲染后的提示词")
    resolved_params: dict = Field(..., description="解析后的参数（含尺寸等）")
    variables_used: dict = Field(..., description="变量填充详情")


class PlatformMediaSpecResponse(BaseModel):
    """平台媒体规范响应"""
    id: int
    platform_type: str
    media_type: str
    spec_name: str
    width: int
    height: int
    max_file_size: int | None = None
    format: str | None = None
    duration_range: dict | None = None
    extra_rules: dict | None = None
