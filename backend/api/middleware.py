"""
API中间件
"""
from typing import Annotated, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantDep
from core.exceptions import QuotaExceededException
from services import QuotaService


async def check_conversation_quota(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    检查对话次数配额（依赖注入）

    用于创建会话、发送消息等场景
    """
    quota_service = QuotaService(db)
    await quota_service.check_conversation_quota(tenant_id)
    return tenant_id


async def check_concurrent_quota(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    检查并发会话配额（依赖注入）

    用于创建新会话时检查
    """
    from services.conversation_service import ConversationService

    quota_service = QuotaService(db)
    conversation_service = ConversationService(db, tenant_id)  # 传递tenant_id

    # 获取当前活跃会话数（不需要传递参数，服务内部会使用self.tenant_id）
    active_count = await conversation_service.get_active_conversation_count()
    await quota_service.check_concurrent_quota(tenant_id, active_count)

    return tenant_id


async def check_storage_quota(
    tenant_id: TenantDep,
    db: DBDep,
    file_size: float = 0.0,
):
    """
    检查存储空间配额（依赖注入）

    用于上传文件、添加知识库等场景

    Args:
        file_size: 需要新增的文件大小(MB)，会转换为GB
    """
    quota_service = QuotaService(db)
    # 转换MB到GB
    size_gb = file_size / 1024 if file_size > 0 else 0
    await quota_service.check_storage_quota(tenant_id, size_gb)
    return tenant_id


async def check_api_quota(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    检查API调用配额（依赖注入）

    用于API接口调用
    """
    quota_service = QuotaService(db)
    await quota_service.check_api_quota(tenant_id)
    return tenant_id


# 组合依赖注入（同时检查多个配额）
ConversationQuotaDep = Annotated[str, Depends(check_conversation_quota)]
ConcurrentQuotaDep = Annotated[str, Depends(check_concurrent_quota)]
StorageQuotaDep = Annotated[str, Depends(check_storage_quota)]
ApiQuotaDep = Annotated[str, Depends(check_api_quota)]
