"""
测试配置管理
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """测试环境配置"""

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============ 基础配置 ============
    base_url: str = "http://127.0.0.1:8000"
    api_prefix: str = "/api/v1"

    # ============ 超时设置 ============
    request_timeout: int = 300  # 增加到300秒，应对慢速数据库操作
    llm_request_timeout: int = 600  # 增加到600秒，支持复杂的AI操作

    # ============ 并发设置 ============
    max_concurrent: int = 10

    # ============ 管理员账号 ============
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # ============ 测试控制 ============
    cleanup_after_test: bool = True
    skip_performance: bool = False
    skip_security: bool = False

    # ============ 日志配置 ============
    log_level: str = "INFO"

    # ============ 测试数据配置 ============
    tenant_prefix: str = "auto_test_"

    # ============ 性能测试配置 ============
    concurrent_users: int = 10
    performance_duration: int = 30

    # ============ LLM 配置 ============
    llm_provider: Literal["zhipuai", "openai", "anthropic", "deepseek"] = "deepseek"

    # 智谱AI配置
    zhipuai_api_key: str = ""
    zhipuai_model: str = "glm-4-flash"

    # OpenAI配置
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_base_url: str = "https://api.openai.com/v1"
    
    # DeepSeek配置
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    @property
    def full_url(self) -> str:
        """获取完整的API URL"""
        return f"{self.base_url}{self.api_prefix}"

    @property
    def has_admin_credentials(self) -> bool:
        """是否配置了管理员凭证"""
        return bool(self.admin_username and self.admin_password)

    @property
    def has_llm_config(self) -> bool:
        """是否配置了LLM"""
        if self.llm_provider == "zhipuai":
            return bool(self.zhipuai_api_key)
        elif self.llm_provider == "openai":
            return bool(self.openai_api_key)
        elif self.llm_provider == "deepseek":
            return bool(self.deepseek_api_key)
        return False


# 全局配置实例
settings = TestSettings()
