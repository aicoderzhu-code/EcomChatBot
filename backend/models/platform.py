"""
平台对接配置模型
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class PlatformConfig(TenantBaseModel):
    """平台对接配置表"""

    __tablename__ = "platform_configs"
    __table_args__ = (
        Index("idx_platform_config_tenant_type_shop", "tenant_id", "platform_type", "shop_id"),
        {"comment": "电商平台对接配置表"},
    )

    # 平台标识
    platform_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="平台类型(pinduoduo/taobao等)"
    )

    # OAuth 凭证
    app_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="平台 App Key")
    app_secret: Mapped[str] = mapped_column(String(512), nullable=False, comment="平台 App Secret(加密存储)")
    access_token: Mapped[str | None] = mapped_column(String(512), comment="访问令牌")
    refresh_token: Mapped[str | None] = mapped_column(String(512), comment="刷新令牌")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="令牌过期时间")

    # 店铺信息
    shop_id: Mapped[str | None] = mapped_column(String(64), comment="店铺ID")
    shop_name: Mapped[str | None] = mapped_column(String(128), comment="店铺名称")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已激活(完成授权)")

    # AI 回复配置
    auto_reply_threshold: Mapped[float] = mapped_column(
        Float, default=0.7, comment="自动回复置信度阈值(0-1)"
    )
    human_takeover_message: Mapped[str | None] = mapped_column(
        Text, comment="转人工提示语"
    )

    def __repr__(self) -> str:
        return f"<PlatformConfig {self.platform_type} tenant={self.tenant_id}>"
