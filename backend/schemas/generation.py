"""内容生成 Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import TimestampSchema


class GenerateRequest(BaseModel):
    """生成请求"""
    product_id: int | None = Field(None, description="商品ID")
    task_type: str = Field(..., pattern="^(poster|video|title|description)$", description="任务类型")
    prompt: str = Field(..., min_length=1, description="提示词")
    template_id: int | None = Field(None, description="模板ID")
    model_config_id: int | None = Field(None, description="模型配置ID")
    params: dict | None = Field(None, description="生成参数")


class GenerationTaskResponse(TimestampSchema):
    """生成任务响应"""
    id: int
    tenant_id: str
    product_id: int | None = None
    task_type: str
    status: str
    prompt: str
    model_config_id: int | None = None
    template_id: int | None = None
    params: dict | None = None
    result_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GeneratedAssetResponse(TimestampSchema):
    """生成资产响应"""
    id: int
    tenant_id: str
    task_id: int
    product_id: int | None = None
    asset_type: str
    file_url: str | None = None
    content: str | None = None
    thumbnail_url: str | None = None
    meta_info: dict | None = Field(None, alias="meta_info", serialization_alias="metadata")
    platform_url: str | None = None
    is_selected: bool


class UploadAssetRequest(BaseModel):
    """上传资产到平台"""
    asset_id: int = Field(..., description="资产ID")
    platform_config_id: int = Field(..., description="平台配置ID")
