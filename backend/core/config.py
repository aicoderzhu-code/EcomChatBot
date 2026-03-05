"""
应用配置管理
"""
import os
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env.production" if os.getenv("DEPLOY_ENV", "production") == "production" else ".env.development",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "电商智能客服系统"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    # 部署环境配置
    deploy_env: str = Field(default="production", description="部署环境：development 或 production")
    host_ip: str = Field(default="localhost", description="开发环境主机IP")

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # Redis
    redis_url: RedisDsn
    redis_max_connections: int = 50

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 8
    jwt_refresh_token_expire_days: int = 30

    # API Key
    api_key_prefix: str = "eck_"
    api_key_length: int = 32

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    openai_base_url: str | None = None

    # Milvus
    milvus_uri: str = ""
    milvus_token: str = ""

    # LLM 配置
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    default_llm_model: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7

    # Azure OpenAI（可选）
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-01"

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ============ 存储配置 ============
    storage_backend: str = "tos"  # 固定使用 tos

    # 火山引擎 TOS 配置
    tos_access_key: str = ""
    tos_secret_key: str = ""
    tos_endpoint: str = "tos-cn-beijing.volces.com"
    tos_region: str = "cn-beijing"
    tos_bucket: str = "ecom-chatbot"

    # RabbitMQ & Celery
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # Concurrent Sessions (系统级保护，防止单租户耗尽资源)
    max_concurrent_sessions_per_tenant: int = 100

    # Monitoring
    prometheus_port: int = 9090
    sentry_dsn: str | None = None

    # Alert
    dingtalk_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    alert_webhook_url: str | None = None
    alert_email_recipients: str = ""
    alert_sms_phones: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@example.com"

    # Webhook
    webhook_timeout: int = 10
    webhook_max_retries: int = 3

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # ============ 支付宝官方 SDK 配置 ============
    alipay_app_id: str = ""
    alipay_private_key: str = ""  # PEM 格式私钥字符串
    alipay_public_key: str = ""   # 支付宝平台公钥字符串
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    alipay_notify_url: str = ""
    alipay_sandbox: bool = False
    alipay_sandbox_gateway: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"

    # ============ 微信支付配置 ============
    wechat_mch_id: str = ""                    # 商户号
    wechat_app_id: str = ""                    # 应用ID
    wechat_api_v3_key: str = ""                # APIv3密钥
    wechat_private_key: str = ""               # 商户API私钥（PEM格式）
    wechat_serial_no: str = ""                 # 商户证书序列号
    wechat_notify_url: str = ""                # 回调地址

    # ============ 拼多多开放平台配置 ============
    pdd_app_key: str = ""
    pdd_app_secret: str = ""
    pdd_webhook_token: str = ""
    pdd_api_base_url: str = "https://gw-api.pinduoduo.com/api/router"
    # AI 介入阈值：置信度低于此值时转人工
    pdd_ai_confidence_threshold: float = 0.6
    # 触发转人工的关键词
    pdd_human_takeover_keywords: list[str] = ["转人工", "人工客服", "真人", "投诉", "退款"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """解析 CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def database_url_str(self) -> str:
        """获取数据库 URL 字符串"""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """获取 Redis URL 字符串"""
        return str(self.redis_url)


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


settings = get_settings()
