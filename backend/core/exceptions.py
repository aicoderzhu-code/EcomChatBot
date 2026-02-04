"""
自定义异常
"""


class AppException(Exception):
    """基础应用异常"""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# 认证相关异常
class AuthenticationException(AppException):
    """认证失败异常"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(message, "AUTH_FAILED")


class InvalidTokenException(AppException):
    """无效的 Token"""

    def __init__(self, message: str = "Token 无效或已过期"):
        super().__init__(message, "INVALID_TOKEN")


class InvalidAPIKeyException(AppException):
    """无效的 API Key"""

    def __init__(self, message: str = "API Key 无效"):
        super().__init__(message, "INVALID_API_KEY")


class AccountLockedException(AppException):
    """账号已锁定"""

    def __init__(self, message: str = "账号已被锁定"):
        super().__init__(message, "ACCOUNT_LOCKED")


# 权限相关异常
class InsufficientPermissionException(AppException):
    """权限不足异常"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "INSUFFICIENT_PERMISSION")


# 资源相关异常
class ResourceNotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} {resource_id} 不存在"
        super().__init__(message, "RESOURCE_NOT_FOUND")


class TenantNotFoundException(ResourceNotFoundException):
    """租户不存在"""

    def __init__(self, tenant_id: str):
        super().__init__("租户", tenant_id)


class ConversationNotFoundException(ResourceNotFoundException):
    """会话不存在"""

    def __init__(self, conversation_id: str):
        super().__init__("会话", conversation_id)


class AdminNotFoundException(ResourceNotFoundException):
    """管理员不存在"""

    def __init__(self, admin_id: str):
        super().__init__("管理员", admin_id)


# 业务逻辑异常
class QuotaExceededException(AppException):
    """配额超限异常"""

    def __init__(self, quota_type: str, message: str | None = None):
        if not message:
            message = f"{quota_type}配额已用完，请升级套餐"
        super().__init__(message, "QUOTA_EXCEEDED")


class SubscriptionExpiredException(AppException):
    """订阅已过期"""

    def __init__(self, message: str = "订阅已过期，请续费"):
        super().__init__(message, "SUBSCRIPTION_EXPIRED")


class TenantSuspendedException(AppException):
    """租户已暂停"""

    def __init__(self, message: str = "租户服务已暂停"):
        super().__init__(message, "TENANT_SUSPENDED")


class FeatureNotEnabledException(AppException):
    """功能未开通"""

    def __init__(self, feature: str):
        message = f"功能模块 {feature} 未开通，请联系管理员"
        super().__init__(message, "FEATURE_NOT_ENABLED")


# 数据验证异常
class ValidationException(AppException):
    """数据验证异常"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class DuplicateResourceException(AppException):
    """资源重复异常"""

    def __init__(self, resource_type: str, field: str, value: str):
        message = f"{resource_type}的{field} '{value}' 已存在"
        super().__init__(message, "DUPLICATE_RESOURCE")


# 外部服务异常
class ExternalServiceException(AppException):
    """外部服务异常"""

    def __init__(self, service: str, message: str):
        super().__init__(f"{service}服务异常: {message}", "EXTERNAL_SERVICE_ERROR")


class LLMServiceException(ExternalServiceException):
    """LLM 服务异常"""

    def __init__(self, message: str):
        super().__init__("LLM", message)


class VectorDBException(ExternalServiceException):
    """向量数据库异常"""

    def __init__(self, message: str):
        super().__init__("向量数据库", message)


# 支付相关异常
class PaymentException(AppException):
    """支付异常"""

    def __init__(self, message: str):
        super().__init__(message, "PAYMENT_ERROR")


class BillNotFoundException(ResourceNotFoundException):
    """账单不存在"""

    def __init__(self, bill_id: int):
        super().__init__("账单", str(bill_id))
