"""
Sentry错误追踪集成
"""
import logging

logger = logging.getLogger(__name__)


def init_sentry(dsn: str, environment: str, traces_sample_rate: float = 0.1):
    """
    初始化Sentry

    Args:
        dsn: Sentry DSN
        environment: 环境名称 (production/staging/development)
        traces_sample_rate: 性能追踪采样率 (0-1)
    """
    if not dsn:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # 配置日志集成
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # 捕获INFO及以上级别
            event_level=logging.ERROR,  # 发送ERROR及以上级别到Sentry
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                logging_integration,
            ],
            # 设置发布版本（可选）
            # release=f"{app_name}@{app_version}",
            # 过滤敏感数据
            before_send=before_send_hook,
            # 配置错误采样
            sample_rate=1.0,  # 100%采样率
            # 设置最大面包屑数量
            max_breadcrumbs=50,
            # 附加请求数据
            send_default_pii=False,  # 不发送个人身份信息
        )

        logger.info(f"Sentry initialized for environment: {environment}")

    except ImportError:
        logger.error(
            "sentry-sdk not installed. Install it with: pip install sentry-sdk[fastapi]"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_hook(event, hint):
    """
    Sentry事件发送前的钩子函数

    用于过滤敏感数据
    """
    # 过滤敏感请求头
    if "request" in event:
        headers = event["request"].get("headers", {})

        # 移除敏感头部
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    # 过滤敏感环境变量
    if "extra" in event:
        extra = event["extra"]
        if "sys.argv" in extra:
            # 过滤命令行参数中的敏感信息
            pass

    return event


def capture_exception(error: Exception, context: dict = None):
    """
    手动捕获异常

    Args:
        error: 异常对象
        context: 额外上下文信息
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)

            sentry_sdk.capture_exception(error)
    except ImportError:
        logger.error("Sentry not available, cannot capture exception")
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {e}")


def capture_message(message: str, level: str = "info", context: dict = None):
    """
    手动捕获消息

    Args:
        message: 消息内容
        level: 严重程度 (debug/info/warning/error/fatal)
        context: 额外上下文信息
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)

            sentry_sdk.capture_message(message, level)
    except ImportError:
        logger.error("Sentry not available, cannot capture message")
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {e}")


def set_user_context(tenant_id: str = None, user_id: str = None, email: str = None):
    """
    设置用户上下文

    Args:
        tenant_id: 租户ID
        user_id: 用户ID
        email: 用户邮箱
    """
    try:
        import sentry_sdk

        sentry_sdk.set_user(
            {"id": user_id, "tenant_id": tenant_id, "email": email}
        )
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set user context in Sentry: {e}")


def set_tag(key: str, value: str):
    """
    设置标签

    Args:
        key: 标签键
        value: 标签值
    """
    try:
        import sentry_sdk

        sentry_sdk.set_tag(key, value)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set tag in Sentry: {e}")


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: dict = None):
    """
    添加面包屑

    Args:
        message: 消息
        category: 分类
        level: 级别
        data: 额外数据
    """
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message, category=category, level=level, data=data or {}
        )
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to add breadcrumb in Sentry: {e}")
