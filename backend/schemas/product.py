"""商品相关 Pydantic Schema"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import BaseSchema, TimestampSchema


# ===== Product Schemas =====

class ProductBase(BaseSchema):
    """商品基础 Schema"""
    title: str = Field(..., min_length=1, max_length=512, description="商品标题")
    description: str | None = Field(None, description="商品描述")
    price: float = Field(..., ge=0, description="当前售价")
    original_price: float | None = Field(None, ge=0, description="原价")
    currency: str = Field("CNY", max_length=8, description="货币")
    category: str | None = Field(None, max_length=128, description="商品分类")
    images: list[str] | None = Field(None, description="商品图片URL列表")
    videos: list[str] | None = Field(None, description="商品视频URL列表")
    attributes: dict | None = Field(None, description="SKU属性")
    sales_count: int = Field(0, ge=0, description="销量")
    stock: int = Field(0, ge=0, description="库存")


class ProductResponse(ProductBase, TimestampSchema):
    """商品响应"""
    id: int
    tenant_id: str
    platform_config_id: int
    platform_product_id: str
    status: str
    knowledge_base_id: int | None = None
    last_synced_at: datetime | None = None
    platform_data: dict | None = None


class ProductListQuery(BaseModel):
    """商品列表查询参数"""
    keyword: str | None = Field(None, description="搜索关键词")
    category: str | None = Field(None, description="分类筛选")
    status: str | None = Field(None, pattern="^(active|inactive|deleted)$", description="状态筛选")
    platform_config_id: int | None = Field(None, description="平台筛选")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")


# ===== Sync Task Schemas =====

class SyncTaskResponse(TimestampSchema):
    """同步任务响应"""
    id: int
    tenant_id: str
    platform_config_id: int
    sync_target: str
    sync_type: str
    status: str
    total_count: int
    synced_count: int
    failed_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TriggerSyncRequest(BaseModel):
    """触发同步请求"""
    platform_config_id: int = Field(..., description="平台配置ID")
    sync_type: str = Field("full", pattern="^(full|incremental)$", description="同步类型")


# ===== Sync Schedule Schemas =====

class SyncScheduleResponse(TimestampSchema):
    """同步调度响应"""
    id: int
    tenant_id: str
    platform_config_id: int
    interval_minutes: int
    is_active: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class SyncScheduleUpdate(BaseModel):
    """更新同步调度"""
    interval_minutes: int | None = Field(None, ge=10, le=1440, description="同步间隔(分钟)")
    is_active: bool | None = Field(None, description="是否启用")
