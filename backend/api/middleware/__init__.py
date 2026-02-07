"""
API中间件模块
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


async def check_conversation_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查对话配额的依赖函数（用于API路由）
    同时完成租户认证和配额检查,返回tenant_id
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_api_key(x_api_key)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )

    # 检查租户访问权限
    await tenant_service.check_tenant_access(tenant.tenant_id)

    # 检查对话配额
    from services.quota_service import QuotaService
    quota_service = QuotaService(db)

    try:
        await quota_service.check_conversation_quota(tenant.tenant_id)
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

    return tenant.tenant_id


async def check_concurrent_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查并发会话配额的依赖函数
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_api_key(x_api_key)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )

    # 检查租户访问权限
    await tenant_service.check_tenant_access(tenant.tenant_id)

    # 并发配额检查会在实际使用时通过ConcurrentQuotaManager进行
    # 这里只是完成认证和基本检查

    return tenant.tenant_id


async def check_storage_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查存储配额的依赖函数
    用于知识库创建等需要消耗存储空间的操作
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_api_key(x_api_key)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )

    # 检查租户访问权限
    await tenant_service.check_tenant_access(tenant.tenant_id)

    # 存储配额检查会在具体操作时进行
    # 这里只是完成认证和基本检查

    return tenant.tenant_id


async def check_api_quota_dependency(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> str:
    """
    检查API调用配额的依赖函数
    用于所有API调用的配额限制
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_api_key(x_api_key)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )

    # 检查租户访问权限
    await tenant_service.check_tenant_access(tenant.tenant_id)

    # 检查API调用配额
    from services.quota_service import QuotaService
    quota_service = QuotaService(db)

    try:
        await quota_service.check_api_quota(tenant.tenant_id)
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

    return tenant.tenant_id


# 类型别名,用于依赖注入
ConversationQuotaDep = Annotated[str, Depends(check_conversation_quota_dependency)]
ConcurrentQuotaDep = Annotated[str, Depends(check_concurrent_quota_dependency)]
StorageQuotaDep = Annotated[str, Depends(check_storage_quota_dependency)]
ApiQuotaDep = Annotated[str, Depends(check_api_quota_dependency)]


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
]