"""
监控相关的Pydantic模型
"""
from pydantic import BaseModel, Field


class ConversationStatsResponse(BaseModel):
    """对话统计响应"""
    total_conversations: int = Field(..., description="总对话数")
    active_conversations: int = Field(..., description="活跃对话数")
    closed_conversations: int = Field(..., description="已关闭对话数")
    avg_messages_per_conversation: float = Field(..., description="平均每对话消息数")
    total_messages: int = Field(..., description="总消息数")
    total_tokens: int = Field(..., description="总Token消耗")


class ResponseTimeStatsResponse(BaseModel):
    """响应时间统计响应"""
    avg_response_time: float = Field(..., description="平均响应时间(ms)")
    min_response_time: int = Field(..., description="最小响应时间(ms)")
    max_response_time: int = Field(..., description="最大响应时间(ms)")
    p50_response_time: float = Field(..., description="P50响应时间(ms)")
    p95_response_time: float = Field(..., description="P95响应时间(ms)")
    p99_response_time: float = Field(..., description="P99响应时间(ms)")


class SatisfactionStatsResponse(BaseModel):
    """满意度统计响应"""
    avg_satisfaction: float = Field(..., description="平均满意度")
    total_ratings: int = Field(..., description="总评分次数")
    distribution: dict[str, int] = Field(..., description="评分分布")
    satisfaction_rate: float = Field(..., description="满意率（4-5分占比%）")


class DashboardSummaryResponse(BaseModel):
    """Dashboard汇总响应"""
    conversation_stats: ConversationStatsResponse
    response_time_stats: ResponseTimeStatsResponse
    satisfaction_stats: SatisfactionStatsResponse
    time_range: str = Field(..., description="时间范围")


class HourlyTrendResponse(BaseModel):
    """每小时趋势响应"""
    hour: str = Field(..., description="小时")
    conversations: int = Field(..., description="对话数")
    messages: int = Field(..., description="消息数")
