"""
LLM模型配置相关数据模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Boolean, Integer, Text, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import TenantBaseModel


class LLMProvider(str, Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    ZHIPUAI = "zhipuai"  # 智谱AI
    DEEPSEEK = "deepseek"  # DeepSeek
    LOCAL_LLM = "local_llm"
    # 可以继续扩展其他提供商


class ModelConfig(TenantBaseModel):
    """LLM模型配置表"""
    __tablename__ = "model_configs"
    __table_args__ = (
        Index("idx_model_config_tenant", "tenant_id"),
        Index("idx_model_config_provider", "provider"),
        Index("idx_model_config_is_default", "is_default"),
        {"comment": "LLM模型配置表"},
    )

    # 提供商信息
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="LLM提供商"
    )
    model_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="模型名称"
    )

    # API配置
    api_key: Mapped[str | None] = mapped_column(
        String(256), comment="API密钥"
    )
    api_base: Mapped[str | None] = mapped_column(
        String(512), comment="API基础URL"
    )

    # 模型参数
    temperature: Mapped[float] = mapped_column(
        Integer, default=0.7, comment="温度参数"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, default=2000, comment="最大Token数"
    )
    top_p: Mapped[float | None] = mapped_column(
        Integer, comment="Top-P采样参数"
    )

    # 高级配置
    advanced_config: Mapped[dict | None] = mapped_column(
        JSON, comment="高级配置（JSON格式）"
    )

    # 使用场景
    use_case: Mapped[str | None] = mapped_column(
        String(64), comment="使用场景(dialogue/rag/translation等)"
    )

    # 状态
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为默认模型"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否激活"
    )

    # 优先级（用于负载均衡）
    priority: Mapped[int] = mapped_column(
        Integer, default=0, comment="优先级（数字越大优先级越高）"
    )

    # 统计信息
    total_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="总调用次数"
    )
    success_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="成功次数"
    )
    failed_calls: Mapped[int] = mapped_column(
        Integer, default=0, comment="失败次数"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, comment="总Token消耗"
    )

    def __repr__(self) -> str:
        return f"<ModelConfig {self.provider}:{self.model_name}>"
