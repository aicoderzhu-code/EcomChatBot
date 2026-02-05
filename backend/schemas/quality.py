"""
质量评估相关的Pydantic模型
"""
from pydantic import BaseModel, Field


class ConversationQualityResponse(BaseModel):
    """对话质量评估响应"""
    conversation_id: str = Field(..., description="对话ID")
    quality_score: float = Field(..., description="质量总分(0-100)", ge=0, le=100)
    metrics: dict = Field(..., description="各项指标得分")
    issues: list[str] = Field(..., description="发现的问题")
    suggestions: list[str] = Field(..., description="改进建议")


class QualitySummaryResponse(BaseModel):
    """质量统计汇总响应"""
    total_conversations: int = Field(..., description="总对话数")
    avg_quality_score: float = Field(..., description="平均质量分")
    score_distribution: dict[str, int] = Field(..., description="分数分布")
    common_issues: list[str] = Field(..., description="常见问题")
