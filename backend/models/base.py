"""
数据库基础模型
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class BaseModel(Base):
    """基础模型（抽象类）"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )


class TenantBaseModel(BaseModel):
    """多租户基础模型（包含 tenant_id）"""

    __abstract__ = True

    tenant_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False, comment="租户ID"
    )
