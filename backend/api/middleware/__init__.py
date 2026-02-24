"""
API中间件模块
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core import decode_token, InvalidTokenException
from db import get_db
from services import TenantService

from .quota import (
    QuotaType,
    OverLimitStrategy,
    QuotaCheckResult,
    check_quota,
    check_concurrent_quota,
    ConcurrentQuotaManager,
)

from .rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter

# HTTP Bearer Token（auto_error=False 允许同时支持 API Key 回退）
_security = HTTPBearer(auto_error=False)


async def _resolve_tenant_id(
    x_api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> str:
    """
    统一租户认证逻辑：优先 API Key，其次 JWT Token。
    与 api.dependencies.get_current_tenant_flexible 保持一致。
    """
    # 优先检查 API Key
    if x_api_key:
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_api_key(x_api_key)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 API Key",
            )
        await tenant_service.check_tenant_access(tenant.tenant_id)
        return tenant.tenant_id

    # 其次检查 JWT Token
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise InvalidTokenException("Token 中缺少租户信息")
            tenant_service = TenantService(db)
            await tenant_service.check_tenant_access(tenant_id)
            return tenant_id
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要 API Key 或 Bearer Token 认证",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _auth_only(
    x_api_key: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """仅做认证，不检查配额"""
    return await _resolve_tenant_id(x_api_key, credentials, db)


# 类型别名，保持与原有路由兼容，但不再检查配额
ConversationQuotaDep = Annotated[str, Depends(_auth_only)]
ConcurrentQuotaDep = Annotated[str, Depends(_auth_only)]
StorageQuotaDep = Annotated[str, Depends(_auth_only)]
ApiQuotaDep = Annotated[str, Depends(_auth_only)]


# CSRF函数
import secrets
import hashlib
import time
from core import settings

def generate_csrf_token(session_id: str = None) -> str:
    """生成 CSRF Token"""
    timestamp = str(int(time.time()))
    random_str = secrets.token_urlsafe(16)
    data = f"{timestamp}:{random_str}"
    if session_id:
        data = f"{session_id}:{data}"

    CSRF_SECRET_KEY = settings.SECRET_KEY
    signature = hashlib.sha256(
        f"{data}:{CSRF_SECRET_KEY}".encode()
    ).hexdigest()[:16]

    return f"{data}.{signature}"


__all__ = [
    "QuotaType",
    "OverLimitStrategy",
    "QuotaCheckResult",
    "check_quota",
    "check_concurrent_quota",
    "ConcurrentQuotaManager",
    "ConversationQuotaDep",
    "ConcurrentQuotaDep",
    "StorageQuotaDep",
    "ApiQuotaDep",
    "RateLimitMiddleware",
    "SlidingWindowRateLimiter",
    "generate_csrf_token",
]