"""
应用配置管理
"""
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "电商智能客服系统"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

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

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20240620"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""

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

    # MinIO/S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ecom-chatbot"
    minio_secure: bool = False

    # RabbitMQ & Celery
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # Monitoring
    prometheus_port: int = 9090
    sentry_dsn: str | None = None

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

    # ============ 支付宝配置 ============
    alipay_appid: str = ""
    alipay_private_key_path: str = "/app/keys/alipay_private_key.pem"
    alipay_public_key_path: str = "/app/keys/alipay_platform_public_key.pem"
    alipay_gateway_url: str = "https://openapi.alipay.com/gateway.do"
    alipay_return_url: str = ""
    alipay_notify_url: str = ""
    alipay_sandbox: bool = True
    alipay_sandbox_gateway: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"

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
