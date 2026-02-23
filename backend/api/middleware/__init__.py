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


async def check_conversation_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查对话配额的依赖函数（用于API路由）
    同时完成租户认证（API Key 或 JWT）和配额检查，返回 tenant_id
    """
    tenant_id = await _resolve_tenant_id(x_api_key, credentials, db)

    # 检查对话配额
    from services.quota_service import QuotaService
    quota_service = QuotaService(db)

    try:
        await quota_service.check_conversation_quota(tenant_id)
    except Exception as e:
        from core.exceptions import QuotaExceededException
        if isinstance(e, QuotaExceededException):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": str(e),
                    "quota_type": "conversation",
                    "upgrade_url": "/pricing"
                }
            )
        raise

    return tenant_id


async def check_concurrent_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查并发会话配额的依赖函数（支持 API Key 和 JWT）
    """
    return await _resolve_tenant_id(x_api_key, credentials, db)


async def check_storage_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查存储配额的依赖函数（支持 API Key 和 JWT）
    用于知识库创建等需要消耗存储空间的操作
    """
    return await _resolve_tenant_id(x_api_key, credentials, db)


async def check_api_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查API调用配额的依赖函数（支持 API Key 和 JWT）
    用于所有API调用的配额限制
    """
    tenant_id = await _resolve_tenant_id(x_api_key, credentials, db)

    # 检查API调用配额
    from services.quota_service import QuotaService
    quota_service = QuotaService(db)

    try:
        await quota_service.check_api_quota(tenant_id)
    except Exception as e:
        from core.exceptions import QuotaExceededException
        if isinstance(e, QuotaExceededException):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": str(e),
                    "quota_type": "api_call",
                    "upgrade_url": "/pricing"
                }
            )
        raise

    return tenant_id


# 类型别名,用于依赖注入
ConversationQuotaDep = Annotated[str, Depends(check_conversation_quota_dependency)]
ConcurrentQuotaDep = Annotated[str, Depends(check_concurrent_quota_dependency)]
StorageQuotaDep = Annotated[str, Depends(check_storage_quota_dependency)]
ApiQuotaDep = Annotated[str, Depends(check_api_quota_dependency)]


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