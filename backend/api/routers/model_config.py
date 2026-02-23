"""
模型配置相关API路由
"""
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse
from schemas.model_config import (
    ModelConfigCreateRequest,
    ModelConfigUpdateRequest,
    ModelConfigResponse,
    ValidateApiKeyRequest,
    ValidateApiKeyResponse,
)
from services.model_config_service import ModelConfigService


router = APIRouter(prefix="/models", tags=["模型配置"])


@router.post("", response_model=ApiResponse[ModelConfigResponse])
async def create_model_config(
    config_data: ModelConfigCreateRequest,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """创建模型配置"""
    service = ModelConfigService(db, tenant_id)
    config = await service.create_model_config(
        provider=config_data.provider,
        model_name=config_data.model_name,
        model_type=config_data.model_type,
        api_key=config_data.api_key,
        api_base=config_data.api_base,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        top_p=config_data.top_p,
        use_case=config_data.use_case,
        is_default=config_data.is_default,
        priority=config_data.priority,
        advanced_config=config_data.advanced_config
    )
    return ApiResponse(data=ModelConfigResponse.model_validate(config))


@router.get("", response_model=ApiResponse[list[ModelConfigResponse]])
async def list_model_configs(
    provider: str | None = None,
    use_case: str | None = None,
    is_active: bool | None = None,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """列出模型配置"""
    service = ModelConfigService(db, tenant_id)
    configs = await service.list_model_configs(
        provider=provider,
        use_case=use_case,
        is_active=is_active
    )
    return ApiResponse(data=[ModelConfigResponse.model_validate(c) for c in configs])


@router.get("/default", response_model=ApiResponse[ModelConfigResponse | None])
async def get_default_model(
    use_case: str | None = None,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """获取默认模型配置"""
    service = ModelConfigService(db, tenant_id)
    config = await service.get_default_model(use_case)
    if config:
        return ApiResponse(data=ModelConfigResponse.model_validate(config))
    return ApiResponse(data=None)


@router.post("/validate-api-key", response_model=ApiResponse[ValidateApiKeyResponse])
async def validate_api_key(
    request: ValidateApiKeyRequest,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """验证 API Key 有效性（向提供商发起最小化请求测试）"""
    result = await ModelConfigService.validate_api_key(
        provider=request.provider,
        api_key=request.api_key,
        api_base=request.api_base,
    )
    return ApiResponse(data=ValidateApiKeyResponse(**result))


@router.get("/{config_id}", response_model=ApiResponse[ModelConfigResponse])
async def get_model_config(
    config_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """获取模型配置详情"""
    service = ModelConfigService(db, tenant_id)
    config = await service.get_model_config(config_id)
    return ApiResponse(data=ModelConfigResponse.model_validate(config))


@router.put("/{config_id}", response_model=ApiResponse[ModelConfigResponse])
async def update_model_config(
    config_id: int,
    config_data: ModelConfigUpdateRequest,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """更新模型配置"""
    service = ModelConfigService(db, tenant_id)
    config = await service.update_model_config(
        config_id=config_id,
        **config_data.model_dump(exclude_unset=True)
    )
    return ApiResponse(data=ModelConfigResponse.model_validate(config))


@router.delete("/{config_id}", response_model=ApiResponse[dict])
async def delete_model_config(
    config_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """删除模型配置"""
    service = ModelConfigService(db, tenant_id)
    await service.delete_model_config(config_id)
    return ApiResponse(data={"message": "删除成功"})


@router.post("/{config_id}/set-default", response_model=ApiResponse[ModelConfigResponse])
async def set_default_model(
    config_id: int,
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """设置默认模型"""
    service = ModelConfigService(db, tenant_id)
    config = await service.update_model_config(config_id, is_default=True)
    return ApiResponse(data=ModelConfigResponse.model_validate(config))
