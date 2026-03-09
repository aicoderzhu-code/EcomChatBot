"""
配额相关 Schemas
"""
from pydantic import BaseModel


class QuotaUsageResponse(BaseModel):
    """配额使用情况响应"""

    billing_period: str
    reply_quota: int
    reply_used: int
    image_gen_quota: int
    image_gen_used: int
    video_gen_quota: int
    video_gen_used: int

    class Config:
        from_attributes = True
