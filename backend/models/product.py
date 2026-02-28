"""商品数据模型"""
import json
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from models.base import TenantBaseModel


class JSONField(TypeDecorator):
    """跨数据库兼容的 JSON 类型"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class ProductStatus(str, PyEnum):
    """商品状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class SyncTarget(str, PyEnum):
    """同步目标"""
    PRODUCT = "product"
    ORDER = "order"


class SyncType(str, PyEnum):
    """同步类型"""
    FULL = "full"
    INCREMENTAL = "incremental"


class SyncTaskStatus(str, PyEnum):
    """同步任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Product(TenantBaseModel):
    """商品表"""

    __tablename__ = "products"
    __table_args__ = (
        Index("idx_product_tenant", "tenant_id"),
        Index("idx_product_platform", "platform_config_id"),
        Index("idx_product_platform_id", "platform_product_id"),
        Index("idx_product_status", "status"),
        Index("idx_product_category", "category"),
        {"comment": "商品表"},
    )

    platform_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="平台配置ID"
    )
    platform_product_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="平台侧商品ID"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="商品标题"
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="商品描述"
    )
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="当前售价"
    )
    original_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="原价"
    )
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, default="CNY", comment="货币"
    )
    category: Mapped[str | None] = mapped_column(
        String(128), comment="商品分类"
    )
    images: Mapped[list | None] = mapped_column(
        JSONField, comment="商品图片URL列表(JSON)"
    )
    videos: Mapped[list | None] = mapped_column(
        JSONField, comment="商品视频URL列表(JSON)"
    )
    attributes: Mapped[dict | None] = mapped_column(
        JSONField, comment="SKU属性(JSON)"
    )
    sales_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="销量"
    )
    stock: Mapped[int] = mapped_column(
        Integer, default=0, comment="库存"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active",
        comment="状态(active/inactive/deleted)"
    )
    platform_data: Mapped[dict | None] = mapped_column(
        JSONField, comment="平台原始数据(JSON)"
    )
    knowledge_base_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联知识库条目ID"
    )
    last_synced_at: Mapped[str | None] = mapped_column(
        DateTime, comment="最近同步时间"
    )

    def __repr__(self) -> str:
        return f"<Product {self.title} ({self.status})>"


class PlatformSyncTask(TenantBaseModel):
    """平台同步任务表"""

    __tablename__ = "platform_sync_tasks"
    __table_args__ = (
        Index("idx_sync_task_tenant", "tenant_id"),
        Index("idx_sync_task_status", "status"),
        {"comment": "平台同步任务表"},
    )

    platform_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="平台配置ID"
    )
    sync_target: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="同步目标(product/order)"
    )
    sync_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="同步类型(full/incremental)"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        comment="状态(pending/running/completed/failed)"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="需同步总数"
    )
    synced_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="已同步数"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="失败数"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, comment="错误信息"
    )
    started_at: Mapped[str | None] = mapped_column(
        DateTime, comment="开始时间"
    )
    completed_at: Mapped[str | None] = mapped_column(
        DateTime, comment="完成时间"
    )

    def __repr__(self) -> str:
        return f"<PlatformSyncTask {self.sync_target}/{self.sync_type} ({self.status})>"


class ProductSyncSchedule(TenantBaseModel):
    """商品同步调度配置表"""

    __tablename__ = "product_sync_schedules"
    __table_args__ = (
        Index("idx_sync_schedule_tenant", "tenant_id"),
        {"comment": "商品同步调度配置表"},
    )

    platform_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="平台配置ID"
    )
    interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, comment="同步间隔(分钟)"
    )
    is_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="是否启用"
    )
    last_run_at: Mapped[str | None] = mapped_column(
        DateTime, comment="上次执行时间"
    )
    next_run_at: Mapped[str | None] = mapped_column(
        DateTime, comment="下次执行时间"
    )

    def __repr__(self) -> str:
        return f"<ProductSyncSchedule platform={self.platform_config_id} interval={self.interval_minutes}m>"
