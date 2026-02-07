"""
API 依赖注入
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core import (
    AdminRole,
    InsufficientPermissionException,
    InvalidAPIKeyException,
    InvalidTokenException,
    decode_token,
    has_permission,
)
from db import get_db, get_redis
from models import Admin
from services import AdminService, TenantService
from services.quota_service import QuotaService

# HTTP Bearer Token
security = HTTPBearer()


async def get_current_tenant_from_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    从 API Key 获取租户 ID（用于租户API认证）

    使用 Redis 缓存以提高性能，缓存时间 5 分钟
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 尝试从 Redis 缓存获取
    from db import get_cache

    cache = await get_cache()
    cache_key = f"api_key:{x_api_key}"
    cached_tenant_id = await cache.get(cache_key)

    if cached_tenant_id:
        # 验证租户访问权限
        tenant_service = TenantService(db)
        await tenant_service.check_tenant_access(cached_tenant_id)
        return cached_tenant_id

    # 缓存未命中，从数据库查询
    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_api_key(x_api_key)

    if not tenant:
        raise InvalidAPIKeyException("无效的 API Key")

    # 检查租户访问权限
    await tenant_service.check_tenant_access(tenant.tenant_id)

    # 缓存结果，5分钟过期
    await cache.set(cache_key, tenant.tenant_id, expire=300)

    return tenant.tenant_id


async def get_current_tenant_from_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """
    从 JWT Token 获取租户 ID（用于租户自用API认证）
    """
    try:
        token = credentials.credentials
        payload = decode_token(token)
        tenant_id = payload.get("tenant_id")

        if not tenant_id:
            raise InvalidTokenException("Token 中缺少租户信息")

        # 验证租户是否存在
        tenant_service = TenantService(db)
        await tenant_service.check_tenant_access(tenant_id)

        return tenant_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Admin:
    """
    从 JWT Token 获取当前管理员（用于管理员API认证）
    """
    try:
        token = credentials.credentials
        payload = decode_token(token)
        admin_id = payload.get("sub")

        if not admin_id:
            raise InvalidTokenException("Token 无效")

        # 获取管理员信息
        admin_service = AdminService(db)
        admin = await admin_service.get_admin(admin_id)

        if admin.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="管理员账号已被禁用",
            )

        return admin
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin_permission(permission: str):
    """
    权限检查装饰器（用于管理员API）

    使用示例:
        @router.post("/path", dependencies=[Depends(require_admin_permission(Permission.TENANT_CREATE))])
    """

    async def permission_checker(
        admin: Annotated[Admin, Depends(get_current_admin)]
    ) -> Admin:
        role = AdminRole(admin.role)
        if not has_permission(role, permission):
            raise InsufficientPermissionException(f"需要权限: {permission}")
        return admin

    return permission_checker


def require_role(*allowed_roles: AdminRole):
    """
    角色检查装饰器（用于管理员API）

    Args:
        allowed_roles: 允许的角色列表

    使用示例:
        @router.post("/path", dependencies=[Depends(require_role(AdminRole.SUPER_ADMIN))])
    """

    async def role_checker(
        admin: Annotated[Admin, Depends(get_current_admin)]
    ) -> Admin:
        role = AdminRole(admin.role)
        if role not in allowed_roles:
            roles_str = ", ".join([r.value for r in allowed_roles])
            raise InsufficientPermissionException(
                f"需要角色: {roles_str}，当前角色: {role.value}"
            )
        return admin

    return role_checker


async def get_quota_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuotaService:
    """
    获取配额服务实例(带Redis支持)
    """
    redis = await get_redis()
    return QuotaService(db, redis)


# 常用依赖注入类型定义
TenantDep = Annotated[str, Depends(get_current_tenant_from_api_key)]
TenantTokenDep = Annotated[str, Depends(get_current_tenant_from_token)]
AdminDep = Annotated[Admin, Depends(get_current_admin)]
DBDep = Annotated[AsyncSession, Depends(get_db)]
QuotaServiceDep = Annotated[QuotaService, Depends(get_quota_service)]
