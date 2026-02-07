"""
敏感词模型
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class SensitiveWord(BaseModel):
    """敏感词表"""

    __tablename__ = "sensitive_words"
    __table_args__ = (
        Index("idx_sensitive_word", "word", unique=True),
        Index("idx_sensitive_category", "category"),
        Index("idx_sensitive_active", "is_active"),
        {"comment": "敏感词表"},
    )

    # 敏感词内容
    word: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="敏感词")

    # 过滤级别: block/replace/warning
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="replace", comment="过滤级别"
    )

    # 分类
    category: Mapped[str] = mapped_column(String(64), nullable=False, comment="分类")

    # 是否启用
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )

    # 创建信息
    created_by: Mapped[str | None] = mapped_column(String(128), comment="创建人")

    # 备注
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")

    def __repr__(self) -> str:
        return f"<SensitiveWord {self.word} ({self.level})>"
