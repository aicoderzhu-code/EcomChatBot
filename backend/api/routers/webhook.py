"""
Webhook相关API路由
"""
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse
from schemas.webhook import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    WebhookResponse,
    WebhookLogResponse
)
from services.webhook_service import WebhookService


router = APIRouter(prefix="/webhooks", tags=["Webhook"])


@router.get("/event-types")
async def get_event_types():
    """获取所有可用的 Webhook 事件类型（公开端点，无需认证）"""
    from models.webhook import WebhookEventType
    
    event_types = [
        {
            "value": event.value,
            "name": event.name,
            "description": event.value.replace(".", " ").replace("_", " ").title()
        }
        for event in WebhookEventType
    ]
    
    return ApiResponse(data={"event_types": event_types})


@router.post("", response_model=ApiResponse[WebhookResponse])
async def create_webhook(
    webhook_data: WebhookCreateRequest,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """创建Webhook配置"""
    service = WebhookService(db, tenant_id)
    webhook = await service.create_webhook(
        name=webhook_data.name,
        endpoint_url=webhook_data.endpoint_url,
        events=webhook_data.events,
        secret=webhook_data.secret
    )
    return ApiResponse(data=WebhookResponse.model_validate(webhook))


@router.get("", response_model=ApiResponse[list[WebhookResponse]])
async def list_webhooks(
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """列出所有Webhook配置"""
    service = WebhookService(db, tenant_id)
    webhooks = await service.list_webhooks()
    return ApiResponse(data=[WebhookResponse.model_validate(w) for w in webhooks])


@router.get("/{webhook_id}", response_model=ApiResponse[WebhookResponse])
async def get_webhook(
    webhook_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """获取Webhook配置详情"""
    service = WebhookService(db, tenant_id)
    webhook = await service.get_webhook(webhook_id)
    return ApiResponse(data=WebhookResponse.model_validate(webhook))


@router.put("/{webhook_id}", response_model=ApiResponse[WebhookResponse])
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdateRequest,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """更新Webhook配置"""
    service = WebhookService(db, tenant_id)
    webhook = await service.update_webhook(
        webhook_id=webhook_id,
        name=webhook_data.name,
        endpoint_url=webhook_data.endpoint_url,
        events=webhook_data.events,
        is_active=webhook_data.is_active
    )
    return ApiResponse(data=WebhookResponse.model_validate(webhook))


@router.delete("/{webhook_id}", response_model=ApiResponse[dict])
async def delete_webhook(
    webhook_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """删除Webhook配置"""
    service = WebhookService(db, tenant_id)
    await service.delete_webhook(webhook_id)
    return ApiResponse(data={"message": "删除成功"})


@router.get("/{webhook_id}/logs", response_model=ApiResponse[list[WebhookLogResponse]])
async def get_webhook_logs(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=200),
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """获取Webhook调用日志"""
    service = WebhookService(db, tenant_id)
    logs = await service.get_webhook_logs(webhook_id, limit)
    return ApiResponse(data=[WebhookLogResponse.model_validate(log) for log in logs])


@router.post("/test/{webhook_id}", response_model=ApiResponse[WebhookLogResponse])
async def test_webhook(
    webhook_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """测试Webhook配置（发送测试事件）"""
    service = WebhookService(db, tenant_id)
    webhook = await service.get_webhook(webhook_id)

    # 发送测试事件
    log = await service.send_webhook(
        webhook=webhook,
        event_type="webhook.test",
        event_data={
            "test": True,
            "message": "这是一条测试消息"
        }
    )

    return ApiResponse(data=WebhookLogResponse.model_validate(log))
