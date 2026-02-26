"""
模型配置相关的Pydantic模型
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ModelConfigCreateRequest(BaseModel):
    """创建模型配置请求"""
    provider: str = Field(..., description="LLM提供商(openai/zhipuai/qwen/siliconflow/meta/private)")
    model_name: str = Field(..., min_length=1, max_length=128, description="模型名称")
    model_type: str = Field("llm", description="模型类型(llm/embedding/rerank)")
    api_key: str | None = Field(None, max_length=512, description="API密钥")
    api_base: str | None = Field(None, max_length=512, description="API基础URL")
    temperature: float = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(2000, ge=0, le=128000, description="最大Token数")
    top_p: float | None = Field(None, ge=0, le=1, description="Top-P参数")
    use_case: str | None = Field(None, max_length=64, description="使用场景(dialogue/rag/translation等)")
    is_default: bool = Field(False, description="是否为默认模型")
    priority: int = Field(0, ge=0, le=100, description="优先级")
    advanced_config: dict | None = Field(None, description="高级配置")


class ModelConfigUpdateRequest(BaseModel):
    """更新模型配置请求"""
    model_name: str | None = Field(None, min_length=1, max_length=128, description="模型名称")
    model_type: str | None = Field(None, description="模型类型(llm/embedding/rerank)")
    api_key: str | None = Field(None, max_length=512, description="API密钥")
    api_base: str | None = Field(None, max_length=512, description="API基础URL")
    temperature: float | None = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: int | None = Field(None, ge=0, le=128000, description="最大Token数")
    top_p: float | None = Field(None, ge=0, le=1, description="Top-P参数")
    use_case: str | None = Field(None, max_length=64, description="使用场景")
    is_default: bool | None = Field(None, description="是否为默认模型")
    is_active: bool | None = Field(None, description="是否激活")
    priority: int | None = Field(None, ge=0, le=100, description="优先级")
    advanced_config: dict | None = Field(None, description="高级配置")


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: int
    tenant_id: str
    provider: str
    model_name: str
    model_type: str
    api_key: str | None
    api_base: str | None
    temperature: float
    max_tokens: int
    top_p: float | None
    use_case: str | None
    is_default: bool
    is_active: bool
    priority: int
    advanced_config: dict | None
    total_calls: int
    success_calls: int
    failed_calls: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ValidateApiKeyRequest(BaseModel):
    """验证 API Key 请求"""
    provider: str = Field(..., description="提供商名称")
    api_key: str = Field(..., description="API密钥")
    api_base: str | None = Field(None, description="自定义API基础URL（用于代理或兼容接口）")


class ValidateApiKeyResponse(BaseModel):
    """验证 API Key 响应"""
    valid: bool
    message: str


class DiscoverModelsRequest(BaseModel):
    """发现可用模型请求"""
    provider: str = Field(..., description="提供商名称")
    api_key: str = Field(..., description="API密钥")
    api_base: str | None = Field(None, description="自定义API基础URL")


class DiscoveredModel(BaseModel):
    """已发现的模型"""
    name: str = Field(..., description="模型 ID")
    model_type: str = Field(..., description="模型类型(llm/embedding/rerank)")


class DiscoverModelsResponse(BaseModel):
    """发现可用模型响应"""
    models: list[DiscoveredModel]


class BatchSaveModelItem(BaseModel):
    """批量保存中的单个模型项"""
    provider: str = Field(..., description="提供商名称")
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(..., description="模型类型(llm/embedding/rerank)")
    api_key: str = Field(..., description="API密钥")
    api_base: str | None = Field(None, description="自定义API基础URL")


class BatchSaveRequest(BaseModel):
    """批量保存模型配置请求"""
    models: list[BatchSaveModelItem]
