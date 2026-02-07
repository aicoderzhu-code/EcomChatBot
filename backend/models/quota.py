"""
配额相关数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class QuotaAdjustmentLog(BaseModel):
    """配额调整审计日志"""

    __tablename__ = "quota_adjustment_logs"

    # 基本信息
    tenant_id: Mapped[str] = mapped_column(String(50), index=True, comment="租户ID")
    quota_type: Mapped[str] = mapped_column(String(50), comment="配额类型: conversation/api_call/storage/concurrent")

    # 调整信息
    adjustment: Mapped[int] = mapped_column(Integer, comment="调整量: 正数=增加额度, 负数=减少额度")
    before_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="调整前的值")
    after_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="调整后的值")

    # 操作信息
    operator_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="操作人ID")
    operator_type: Mapped[str] = mapped_column(String(20), comment="操作人类型: admin/system/api")
    reason: Mapped[str] = mapped_column(Text, comment="调整原因")

    # 元数据
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="操作IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="用户代理")
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="额外信息(JSON格式)")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return (
            f"<QuotaAdjustmentLog("
            f"id={self.id}, "
            f"tenant_id={self.tenant_id}, "
            f"quota_type={self.quota_type}, "
            f"adjustment={self.adjustment}, "
            f"operator={self.operator_id}"
            f")>"
        )
