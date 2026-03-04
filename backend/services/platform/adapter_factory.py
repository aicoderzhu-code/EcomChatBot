"""平台适配器工厂"""
from models.platform import PlatformConfig
from services.platform.base_adapter import BasePlatformAdapter
from services.platform.pdd_adapter import PddAdapter
from services.platform.douyin_adapter import DouyinAdapter


def create_adapter(config: PlatformConfig) -> BasePlatformAdapter:
    """根据平台配置创建对应的适配器实例"""
    adapters = {
        "pinduoduo": PddAdapter,
        "douyin": DouyinAdapter,
    }

    adapter_class = adapters.get(config.platform_type)
    if not adapter_class:
        raise ValueError(f"不支持的平台类型: {config.platform_type}")

    return adapter_class(
        app_key=config.app_key,
        app_secret=config.app_secret,
        access_token=config.access_token,
    )
