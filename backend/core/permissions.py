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
        Permission.STATISTICS_READ,
    ],
    AdminRole.VIEWER: [
        Permission.TENANT_READ,
        Permission.SUBSCRIPTION_READ,
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


# 新订阅套餐价格和时长配置
SUBSCRIPTION_PLANS = {
    "trial":       {"name": "试用版", "price": 0,   "days": 3},
    "monthly":     {"name": "月付版", "price": 0.1, "days": 30},
    "quarterly":   {"name": "季付版", "price": 0.1, "days": 90},
    "semi_annual": {"name": "半年付", "price": 0.1, "days": 180},
    "annual":      {"name": "年付版", "price": 0.1, "days": 365},
}

# 配额常量定义（AI回复不限量，仅图片/视频有月度配额）
QUOTA_CONFIGS = {
    # 正式套餐配额（月度）
    "standard": {
        "image_gen_quota": 100,
        "video_gen_quota": 10,
    },
    # 试用版配额（减半）
    "trial": {
        "image_gen_quota": 50,
        "video_gen_quota": 5,
    },
}

# 加量包定义（永久有效）
ADDON_PACKAGES = {
    "image_addon": {"name": "图片生成加量包", "price": 0.1, "credits": 50, "credit_type": "image"},
    "video_addon": {"name": "视频生成加量包", "price": 0.1, "credits": 10, "credit_type": "video"},
}


def get_quota_config(plan_type: str) -> dict:
    """根据套餐类型获取配额配置"""
    if plan_type == "trial":
        return QUOTA_CONFIGS["trial"]
    return QUOTA_CONFIGS["standard"]


# 套餐配置（订阅套餐，基于时间段）
PLAN_CONFIGS = {
    "trial": {
        "name": "试用版",
        "base_price": 0,
        "features": [module for module in FeatureModule],
    },
    "monthly": {
        "name": "月付版",
        "base_price": 0.1,
        "features": [module for module in FeatureModule],
    },
    "quarterly": {
        "name": "季付版",
        "base_price": 0.1,
        "features": [module for module in FeatureModule],
    },
    "semi_annual": {
        "name": "半年付",
        "base_price": 0.1,
        "features": [module for module in FeatureModule],
    },
    "annual": {
        "name": "年付版",
        "base_price": 0.1,
        "features": [module for module in FeatureModule],
    },
}
