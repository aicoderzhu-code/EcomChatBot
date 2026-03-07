"""内容生成模型"""
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel
from models.product import JSONField


class GenerationTaskType(str, PyEnum):
    """生成任务类型"""
    POSTER = "poster"
    VIDEO = "video"
    TITLE = "title"
    DESCRIPTION = "description"


class GenerationTaskStatus(str, PyEnum):
    """生成任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(str, PyEnum):
    """资产类型"""
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"


class GenerationTask(TenantBaseModel):
    """内容生成任务表"""

    __tablename__ = "generation_tasks"
    __table_args__ = (
        Index("idx_gen_task_tenant", "tenant_id"),
        Index("idx_gen_task_product", "product_id"),
        Index("idx_gen_task_status", "status"),
        {"comment": "内容生成任务表"},
    )

    product_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联商品ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="任务类型(poster/video/title/description)"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        comment="状态(pending/processing/completed/failed)"
    )
    prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="生成提示词"
    )
    model_config_id: Mapped[int | None] = mapped_column(
        Integer, comment="使用的模型配置ID"
    )
    prompt_id: Mapped[int | None] = mapped_column(
        Integer, comment="使用的提示词ID"
    )
    params: Mapped[dict | None] = mapped_column(
        JSONField, comment="生成参数(JSON)"
    )
    result_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="生成结果数量"
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
    template_id: Mapped[int | None] = mapped_column(
        Integer, comment="使用的模板ID"
    )
    scene_type: Mapped[str | None] = mapped_column(
        String(64), comment="场景类型"
    )
    target_platform: Mapped[str | None] = mapped_column(
        String(32), comment="目标平台"
    )
    generation_mode: Mapped[str] = mapped_column(
        String(16), default="advanced", comment="生成模式(simple/advanced)"
    )

    def __repr__(self) -> str:
        return f"<GenerationTask {self.task_type} ({self.status})>"


class GeneratedAsset(TenantBaseModel):
    """生成资产表"""

    __tablename__ = "generated_assets"
    __table_args__ = (
        Index("idx_gen_asset_tenant", "tenant_id"),
        Index("idx_gen_asset_task", "task_id"),
        Index("idx_gen_asset_product", "product_id"),
        {"comment": "生成资产表"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="生成任务ID"
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联商品ID"
    )
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="资产类型(image/video/text)"
    )
    file_url: Mapped[str | None] = mapped_column(
        String(1024), comment="文件URL(对象存储)"
    )
    content: Mapped[str | None] = mapped_column(
        Text, comment="文本内容(用于标题/描述)"
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1024), comment="缩略图URL"
    )
    meta_info: Mapped[dict | None] = mapped_column(
        "metadata", JSONField, comment="元数据(JSON)"
    )
    platform_url: Mapped[str | None] = mapped_column(
        String(1024), comment="已上传到平台的URL"
    )
    is_selected: Mapped[int] = mapped_column(
        Integer, default=0, comment="是否被选中使用"
    )
    scene_type: Mapped[str | None] = mapped_column(
        String(64), comment="场景类型"
    )
    target_platform: Mapped[str | None] = mapped_column(
        String(32), comment="目标平台"
    )
    review_status: Mapped[str] = mapped_column(
        String(16), default="pending", comment="审核状态(pending/approved/rejected)"
    )

    def __repr__(self) -> str:
        return f"<GeneratedAsset {self.asset_type} task={self.task_id}>"
