"""
权限定义和检查
"""
from enum import Enum


class AdminRole(str, Enum):
    """管理员角色"""

    SUPER_ADMIN = "super_admin"  # 超级管理员
    FINANCE_ADMIN = "finance_admin"  # 财务管理员
    SUPPORT_ADMIN = "support_admin"  # 客服管理员
    VIEWER = "viewer"  # 只读权限


class Permission(str, Enum):
    """权限枚举"""

    # 租户管理
    TENANT_READ = "tenant:read"
    TENANT_CREATE = "tenant:create"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_SUSPEND = "tenant:suspend"

    # 订阅管理
    SUBSCRIPTION_READ = "subscription:read"
    SUBSCRIPTION_UPDATE = "subscription:update"
    SUBSCRIPTION_EXTEND = "subscription:extend"

    # 配额管理
    QUOTA_READ = "quota:read"
    QUOTA_ADJUST = "quota:adjust"

    # 账单管理
    BILLING_READ = "billing:read"
    BILLING_UPDATE = "billing:update"
    BILLING_REFUND = "billing:refund"

    # 统计数据
    STATISTICS_READ = "statistics:read"

    # 系统配置
    SYSTEM_CONFIG = "system:config"

    # 管理员管理
    ADMIN_MANAGE = "admin:manage"


# 角色权限映射
ROLE_PERMISSIONS: dict[AdminRole, list[str]] = {
    AdminRole.SUPER_ADMIN: ["*"],  # 所有权限
    AdminRole.FINANCE_ADMIN: [
        Permission.TENANT_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.BILLING_READ,
        Permission.BILLING_UPDATE,
        Permission.BILLING_REFUND,
        Permission.STATISTICS_READ,
    ],
    AdminRole.SUPPORT_ADMIN: [
        Permission.TENANT_READ,
        Permission.TENANT_UPDATE,
        Permission.SUBSCRIPTION_READ,
        Permission.SUBSCRIPTION_EXTEND,
        Permission.QUOTA_READ,
        Permission.QUOTA_ADJUST,
        Permission.STATISTICS_READ,
    ],
    AdminRole.VIEWER: [
        Permission.TENANT_READ,
        Permission.SUBSCRIPTION_READ,
        Permission.QUOTA_READ,
        Permission.BILLING_READ,
        Permission.STATISTICS_READ,
    ],
}


def has_permission(role: AdminRole, permission: str) -> bool:
    """
    检查角色是否有指定权限
    
    Args:
        role: 管理员角色
        permission: 权限标识
    
    Returns:
        是否有权限
    """
    permissions = ROLE_PERMISSIONS.get(role, [])

    # 超级管理员拥有所有权限
    if "*" in permissions:
        return True

    return permission in permissions


class FeatureModule(str, Enum):
    """功能模块"""

    BASIC_CHAT = "basic_chat"  # 基础对话（必选）
    ORDER_QUERY = "order_query"  # 订单查询
    PRODUCT_RECOMMEND = "product_recommend"  # 商品推荐
    AFTER_SALES = "after_sales"  # 售后服务
    DATA_ANALYTICS = "data_analytics"  # 数据分析
    KNOWLEDGE_MANAGE = "knowledge_manage"  # 知识库管理
    API_ACCESS = "api_access"  # API 接口
    ADVANCED_NLU = "advanced_nlu"  # 高级 NLU
    CUSTOM_INTEGRATION = "custom_integration"  # 自定义集成


# 套餐配置
PLAN_CONFIGS = {
    "free": {
        "name": "免费版",
        "base_price": 0,
        "features": [FeatureModule.BASIC_CHAT],
        "conversation_quota": 100,
        "concurrent_quota": 5,
        "storage_quota": 1,  # GB
        "api_quota": 0,
    },
    "basic": {
        "name": "基础版",
        "base_price": 299,
        "features": [
            FeatureModule.BASIC_CHAT,
            FeatureModule.ORDER_QUERY,
            FeatureModule.KNOWLEDGE_MANAGE,
        ],
        "conversation_quota": 2000,
        "concurrent_quota": 50,
        "storage_quota": 10,
        "api_quota": 1000,
    },
    "professional": {
        "name": "专业版",
        "base_price": 999,
        "features": [
            FeatureModule.BASIC_CHAT,
            FeatureModule.ORDER_QUERY,
            FeatureModule.PRODUCT_RECOMMEND,
            FeatureModule.AFTER_SALES,
            FeatureModule.DATA_ANALYTICS,
            FeatureModule.KNOWLEDGE_MANAGE,
            FeatureModule.API_ACCESS,
        ],
        "conversation_quota": 10000,
        "concurrent_quota": 200,
        "storage_quota": 50,
        "api_quota": 10000,
    },
    "enterprise": {
        "name": "企业版",
        "base_price": 2999,
        "features": [module.value for module in FeatureModule],  # 所有功能
        "conversation_quota": 50000,
        "concurrent_quota": 1000,
        "storage_quota": 200,
        "api_quota": 100000,
    },
}
