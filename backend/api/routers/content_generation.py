"""内容生成 API 路由"""
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.generation import (
    GenerateRequest, GeneratedAssetResponse,
    GenerationTaskResponse, UploadAssetRequest,
)
from schemas.product_prompt import (
    ProductPromptCreate, ProductPromptResponse, ProductPromptUpdate,
)
from services.content_generation.generation_service import GenerationService
from services.content_generation.product_prompt_service import ProductPromptService
from services.content_generation.asset_upload_service import AssetUploadService
from services.storage_service import StorageService
from tasks.generation_tasks import run_generation

router = APIRouter(prefix="/content", tags=["内容生成"])


# ===== 商品提示词 =====

@router.get("/prompts", response_model=ApiResponse[PaginatedResponse[ProductPromptResponse]])
async def list_prompts(
    tenant_id: TenantFlexDep,
    db: DBDep,
    product_id: int | None = None,
    prompt_type: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询商品提示词列表"""
    service = ProductPromptService(db, tenant_id)
    prompts, total = await service.list_prompts(
        product_id=product_id, prompt_type=prompt_type, page=page, size=size
    )
    paginated = PaginatedResponse.create(
        items=prompts, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.post("/prompts", response_model=ApiResponse[ProductPromptResponse])
async def create_prompt(
    request: ProductPromptCreate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建商品提示词"""
    service = ProductPromptService(db, tenant_id)
    prompt = await service.create_prompt(
        product_id=request.product_id,
        prompt_type=request.prompt_type,
        name=request.name,
        content=request.content,
    )
    return ApiResponse(data=prompt)


@router.put("/prompts/{prompt_id}", response_model=ApiResponse[ProductPromptResponse])
async def update_prompt(
    prompt_id: int,
    request: ProductPromptUpdate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新商品提示词"""
    service = ProductPromptService(db, tenant_id)
    prompt = await service.update_prompt(
        prompt_id=prompt_id,
        name=request.name,
        content=request.content,
    )
    if not prompt:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "提示词不存在"})
    return ApiResponse(data=prompt)


@router.delete("/prompts/{prompt_id}", response_model=ApiResponse)
async def delete_prompt(
    prompt_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除商品提示词"""
    service = ProductPromptService(db, tenant_id)
    deleted = await service.delete_prompt(prompt_id)
    if not deleted:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "提示词不存在"})
    return ApiResponse(data=None)


# ===== 生成任务 =====

@router.post("/generate", response_model=ApiResponse[GenerationTaskResponse])
async def create_generation(
    request: GenerateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建内容生成任务"""
    service = GenerationService(db, tenant_id)
    task = await service.create_task(
        task_type=request.task_type,
        prompt=request.prompt,
        product_id=request.product_id,
        prompt_id=request.prompt_id,
        model_config_id=request.model_config_id,
        params=request.params,
    )
    # 异步执行
    run_generation.delay(task.id, tenant_id)
    return ApiResponse(data=task)


@router.get("/tasks", response_model=ApiResponse[PaginatedResponse[GenerationTaskResponse]])
async def list_generation_tasks(
    tenant_id: TenantFlexDep,
    db: DBDep,
    task_type: str | None = None,
    product_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询生成任务列表"""
    service = GenerationService(db, tenant_id)
    tasks, total = await service.list_tasks(
        task_type=task_type, product_id=product_id,
        status=status, page=page, size=size,
    )
    paginated = PaginatedResponse.create(
        items=tasks, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.get("/tasks/{task_id}", response_model=ApiResponse[GenerationTaskResponse])
async def get_generation_task(
    task_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取生成任务详情"""
    service = GenerationService(db, tenant_id)
    task = await service.get_task(task_id)
    if not task:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "任务不存在"})
    return ApiResponse(data=task)


@router.post("/tasks/{task_id}/retry", response_model=ApiResponse[GenerationTaskResponse])
async def retry_generation_task(
    task_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """重试失败的生成任务"""
    service = GenerationService(db, tenant_id)
    task = await service.retry_task(task_id)
    if not task:
        return ApiResponse(success=False, error={"code": "INVALID_STATE", "message": "任务不存在或状态不允许重试"})
    # 异步执行
    run_generation.delay(task.id, tenant_id)
    return ApiResponse(data=task)


# ===== 素材 =====

def _extract_minio_object_name(file_url: str) -> str | None:
    """从 MinIO URL（内部或外部地址）中提取 object_name，非 MinIO URL 返回 None"""
    from services.storage_service import MINIO_ENDPOINT, MINIO_EXTERNAL_ENDPOINT, MINIO_BUCKET
    for endpoint in (MINIO_ENDPOINT, MINIO_EXTERNAL_ENDPOINT):
        prefix = f"http://{endpoint}/{MINIO_BUCKET}/"
        if file_url.startswith(prefix):
            path = file_url[len(prefix):]
            return path.split("?")[0]
    return None


def _resolve_asset_urls(assets: list) -> list:
    """对 MinIO 对象路径生成公开访问 URL"""
    for asset in assets:
        if not asset.file_url:
            continue
        if not asset.file_url.startswith("http"):
            asset.file_url = StorageService.get_public_url(asset.file_url)
        else:
            obj_name = _extract_minio_object_name(asset.file_url)
            if obj_name:
                asset.file_url = StorageService.get_public_url(obj_name)
    return assets


@router.get("/assets", response_model=ApiResponse[PaginatedResponse[GeneratedAssetResponse]])
async def list_assets(
    tenant_id: TenantFlexDep,
    db: DBDep,
    task_id: int | None = None,
    product_id: int | None = None,
    asset_type: str | None = None,
    keyword: str | None = None,
    is_selected: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询素材列表"""
    service = GenerationService(db, tenant_id)
    assets, total = await service.list_assets(
        task_id=task_id, product_id=product_id,
        asset_type=asset_type, keyword=keyword,
        is_selected=is_selected, page=page, size=size,
    )
    _resolve_asset_urls(assets)
    paginated = PaginatedResponse.create(
        items=assets, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.delete("/assets/{asset_id}", response_model=ApiResponse)
async def delete_asset(
    asset_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除素材"""
    service = GenerationService(db, tenant_id)
    deleted = await service.delete_asset(asset_id)
    if not deleted:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "素材不存在"})
    return ApiResponse(data=None)


@router.put("/assets/{asset_id}/selected", response_model=ApiResponse[GeneratedAssetResponse])
async def toggle_asset_selected(
    asset_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """切换素材收藏状态"""
    service = GenerationService(db, tenant_id)
    asset = await service.toggle_asset_selected(asset_id)
    if not asset:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "素材不存在"})
    _resolve_asset_urls([asset])
    return ApiResponse(data=asset)


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """生成素材下载链接"""
    service = GenerationService(db, tenant_id)
    asset = await service.get_asset(asset_id)
    if not asset or not asset.file_url:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "素材不存在"})
    if not asset.file_url.startswith("http"):
        url = StorageService.get_public_url(asset.file_url)
        return RedirectResponse(url=url)
    obj_name = _extract_minio_object_name(asset.file_url)
    if obj_name:
        url = StorageService.get_public_url(obj_name)
        return RedirectResponse(url=url)
    return RedirectResponse(url=asset.file_url)


@router.post("/assets/upload", response_model=ApiResponse[dict])
async def upload_asset_to_platform(
    request: UploadAssetRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """上传素材到电商平台"""
    service = AssetUploadService(db, tenant_id)
    try:
        platform_url = await service.upload_to_platform(
            asset_id=request.asset_id,
            platform_config_id=request.platform_config_id,
        )
        return ApiResponse(data={"platform_url": platform_url})
    except ValueError as e:
        return ApiResponse(success=False, error={"code": "UPLOAD_ERROR", "message": str(e)})
