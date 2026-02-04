"""
基础 Schema
"""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """基础 Schema"""

    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应"""

    success: bool = True
    data: T | None = None
    error: dict[str, str] | None = None
    meta: dict[str, any] | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @staticmethod
    def create(items: list[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        """创建分页响应"""
        pages = (total + size - 1) // size
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


class TimestampSchema(BaseSchema):
    """时间戳 Schema"""

    created_at: datetime
    updated_at: datetime
