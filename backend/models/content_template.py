"""内容模板模型"""
from sqlalchemy import Index, Integer, String, Text, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base
from models.base import BaseModel
from models.product import JSONField


class ContentTemplate(BaseModel):
    """内容模板表（支持系统模板和租户自定义模板）"""

    __tablename__ = "content_templates"
    __table_args__ = (
        Index("idx_ct_tenant", "tenant_id"),
        Index("idx_ct_category", "category", "scene_type"),
        {"comment": "内容模板表"},
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="租户ID（NULL表示系统模板）"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="模板名称"
    )
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="模板类别(poster/video)"
    )
    scene_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="场景类型(main_image/detail_image/promo_poster/main_video/short_video/detail_video)"
    )
    prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False, comment="提示词模板（含变量占位符）"
    )
    variables: Mapped[list | None] = mapped_column(
        JSONField, comment="变量定义(JSON数组)"
    )
    style_options: Mapped[list | None] = mapped_column(
        JSONField, comment="风格选项(JSON数组)"
    )
    platform_presets: Mapped[dict | None] = mapped_column(
        JSONField, comment="平台预设参数(JSON对象)"
    )
    default_params: Mapped[dict | None] = mapped_column(
        JSONField, comment="默认生成参数(JSON对象)"
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1024), comment="缩略图URL"
    )
    is_system: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0"), comment="是否系统模板(0否1是)"
    )
    is_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=sa_text("1"), comment="是否启用(0否1是)"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0"), comment="排序顺序"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0"), comment="使用次数"
    )

    def __repr__(self) -> str:
        return f"<ContentTemplate {self.name} ({self.category}/{self.scene_type})>"


class PlatformMediaSpec(Base):
    """平台媒体规范表（非多租户表）"""

    __tablename__ = "platform_media_specs"
    __table_args__ = (
        Index("idx_pms_unique", "platform_type", "media_type", unique=True),
        {"comment": "平台媒体规范表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="平台类型(taobao/pdd/douyin/jd/kuaishou)"
    )
    media_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="媒体类型(main_image/detail_image/main_video/short_video)"
    )
    spec_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="规范名称"
    )
    width: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="宽度(像素)"
    )
    height: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="高度(像素)"
    )
    max_file_size: Mapped[int | None] = mapped_column(
        Integer, comment="最大文件大小(字节)"
    )
    format: Mapped[str | None] = mapped_column(
        String(64), comment="支持格式(逗号分隔)"
    )
    duration_range: Mapped[dict | None] = mapped_column(
        JSONField, comment="时长范围(JSON对象，视频专用)"
    )
    extra_rules: Mapped[dict | None] = mapped_column(
        JSONField, comment="额外规则(JSON对象)"
    )

    def __repr__(self) -> str:
        return f"<PlatformMediaSpec {self.platform_type}/{self.media_type}>"

