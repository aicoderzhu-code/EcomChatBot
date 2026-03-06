"""ISV 应用管理模型"""
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class PlatformApp(BaseModel):
    """ISV 在各电商平台注册的应用信息（全局，非租户级别）"""

    __tablename__ = "platform_apps"
    __table_args__ = {"comment": "ISV 平台应用配置表"}

    # 平台标识（唯一）
    platform_type: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="平台类型"
    )

    # 应用信息
    app_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="应用名称")
    app_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="应用 Key")
    app_secret: Mapped[str] = mapped_column(String(512), nullable=False, comment="应用 Secret(加密)")

    # 回调配置
    callback_url: Mapped[str | None] = mapped_column(Text, comment="OAuth 回调地址")
    webhook_url: Mapped[str | None] = mapped_column(Text, comment="Webhook 接收地址")

    # 权限和配置
    scopes: Mapped[dict | None] = mapped_column(JSON, comment="申请的权限列表")
    status: Mapped[str] = mapped_column(
        String(16), default="active", comment="状态(active/inactive/reviewing)"
    )
    extra_config: Mapped[dict | None] = mapped_column(JSON, comment="平台特有配置")

    def __repr__(self) -> str:
        return f"<PlatformApp {self.platform_type} ({self.app_name})>"
