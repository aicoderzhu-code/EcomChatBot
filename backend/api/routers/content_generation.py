"""内容生成 API 路由"""
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.generation import (
    GenerateRequest, GeneratedAssetResponse,
    GenerationTaskResponse, UploadAssetRequest,
    BatchGenerateRequest, ReviewAssetRequest, BatchUploadAssetsRequest,
)
from schemas.content_template import (
    ContentTemplateResponse, ContentTemplateCreate,
    TemplateRenderRequest, TemplateRenderResponse,
    PlatformMediaSpecResponse,
)
from schemas.product_prompt import (
    ProductPromptCreate, ProductPromptResponse, ProductPromptUpdate,
)
from services.content_generation.generation_service import GenerationService
from services.content_generation.product_prompt_service import ProductPromptService
from services.content_generation.asset_upload_service import AssetUploadService
from services.content_generation.template_service import TemplateService
from services.content_generation.platform_spec_service import PlatformSpecService
from services.content_generation.provider_capabilities import get_capabilities
from services.storage_service import StorageService
from services.quota_service import QuotaService, QuotaExceededError
from tasks.generation_tasks import run_generation

router = APIRouter(prefix="/content", tags=["内容生成"])


# ===== Provider 能力 =====

@router.get("/provider-capabilities", response_model=ApiResponse[dict])
async def get_provider_capabilities(
    task_type: str = Query(..., description="任务类型: poster / video"),
):
    """获取各 provider 的能力描述，供前端动态渲染表单"""
    caps = get_capabilities(task_type)
    return ApiResponse(data=caps)


# ===== 场景模板 =====

@router.get("/templates", response_model=ApiResponse[PaginatedResponse[ContentTemplateResponse]])
async def list_templates(
    tenant_id: TenantFlexDep,
    db: DBDep,
    category: str | None = Query(None, description="模板类别: poster / video"),
    scene_type: str | None = Query(None, description="场景类型"),
    platform: str | None = Query(None, description="目标平台"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询模板列表（系统模板 + 租户自定义模板）"""
    service = TemplateService(db, tenant_id)
    templates, total = await service.list_templates(
        category=category, scene_type=scene_type,
        platform=platform, page=page, page_size=size,
    )
    paginated = PaginatedResponse.create(
        items=templates, total=total, page=page, size=size
    )
    return ApiResponse(data=paginated)


@router.post("/templates", response_model=ApiResponse[ContentTemplateResponse])
async def create_template(
    request: ContentTemplateCreate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建租户自定义模板"""
    service = TemplateService(db, tenant_id)
    template = await service.create_template(
        name=request.name,
        category=request.category,
        scene_type=request.scene_type,
        prompt_template=request.prompt_template,
        variables=request.variables,
        style_options=request.style_options,
        platform_presets=request.platform_presets,
        default_params=request.default_params,
        thumbnail_url=request.thumbnail_url,
    )
    return ApiResponse(data=template)


@router.get("/templates/{template_id}", response_model=ApiResponse[ContentTemplateResponse])
async def get_template(
    template_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取模板详情"""
    service = TemplateService(db, tenant_id)
    template = await service.get_template(template_id)
    if not template:
        return ApiResponse(success=False, error={"code": "NOT_FOUND", "message": "模板不存在"})
    return ApiResponse(data=template)


@router.post("/templates/{template_id}/render", response_model=ApiResponse[TemplateRenderResponse])
async def render_template(
    template_id: int,
    request: TemplateRenderRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """渲染模板（变量替换）"""
    service = TemplateService(db, tenant_id)
    try:
        result = await service.render_template(
            template_id=template_id,
            product_id=request.product_id,
            overrides=request.overrides,
            target_platform=request.target_platform,
        )
        return ApiResponse(data=result)
    except ValueError as e:
        return ApiResponse(success=False, error={"code": "RENDER_ERROR", "message": str(e)})


# ===== 平台规范 =====

@router.get("/platform-specs", response_model=ApiResponse[list[PlatformMediaSpecResponse]])
async def list_platform_specs(
    db: DBDep,
    platform_type: str | None = Query(None, description="平台类型"),
    media_type: str | None = Query(None, description="媒体类型"),
):
    """查询平台媒体规范列表"""
    service = PlatformSpecService(db)
    specs = await service.list_specs(
        platform_type=platform_type,
        media_type=media_type,
    )
    return ApiResponse(data=specs)


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
    # 检查配额
    quota_service = QuotaService(db)
    try:
        if request.task_type == "poster":
            await quota_service.check_image_quota(tenant_id)
        elif request.task_type == "video":
            await quota_service.check_video_quota(tenant_id)
        else:
            # title/description 使用 LLM，消耗回复配额
            await quota_service.check_reply_quota(tenant_id)
    except QuotaExceededError as e:
        return ApiResponse(
            success=False,
            error={"code": "QUOTA_EXCEEDED", "message": str(e)},
        )

    service = GenerationService(db, tenant_id)
    task = await service.create_task(
        task_type=request.task_type,
        prompt=request.prompt,
        product_id=request.product_id,
        prompt_id=request.prompt_id,
        model_config_id=request.model_config_id,
        params=request.params,
        template_id=request.template_id,
        scene_type=request.scene_type,
        target_platform=request.target_platform,
        generation_mode=request.generation_mode,
    )

    # 扣减配额
    if request.task_type == "poster":
        await quota_service.increment_image(tenant_id)
    elif request.task_type == "video":
        await quota_service.increment_video(tenant_id)
    else:
        await quota_service.increment_reply(tenant_id)
    await db.commit()

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


# ===== 批量操作 =====

@router.post("/batch-generate", response_model=ApiResponse[list[GenerationTaskResponse]])
async def batch_generate(
    request: BatchGenerateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """批量生成（多商品 x 同模板）"""
    service = GenerationService(db, tenant_id)
    try:
        tasks = await service.batch_generate(
            template_id=request.template_id,
            product_ids=request.product_ids,
            target_platform=request.target_platform,
            params=request.params,
        )
        # 异步执行所有任务
        for task in tasks:
            run_generation.delay(task.id, tenant_id)
        return ApiResponse(data=tasks)
    except ValueError as e:
        return ApiResponse(success=False, error={"code": "BATCH_ERROR", "message": str(e)})


# ===== 素材 =====

def _resolve_asset_urls(assets: list) -> list:
    """为对象路径生成公开访问 URL"""
    for asset in assets:
        if not asset.file_url:
            continue
        # 如果不是完整URL，则生成预签名URL
        if not asset.file_url.startswith("http"):
            asset.file_url = StorageService.get_public_url(asset.file_url)
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
    scene_type: str | None = None,
    target_platform: str | None = None,
    review_status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询素材列表"""
    service = GenerationService(db, tenant_id)
    assets, total = await service.list_assets(
        task_id=task_id, product_id=product_id,
        asset_type=asset_type, keyword=keyword,
        is_selected=is_selected, scene_type=scene_type,
        target_platform=target_platform, review_status=review_status,
        page=page, size=size,
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


@router.put("/assets/{asset_id}/review", response_model=ApiResponse[GeneratedAssetResponse])
async def review_asset(
    asset_id: int,
    request: ReviewAssetRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """审核素材（approved/rejected）"""
    service = GenerationService(db, tenant_id)
    asset = await service.review_asset(
        asset_id=asset_id,
        review_status=request.review_status,
        note=request.note,
    )
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
    # 如果不是完整URL，生成预签名URL
    if not asset.file_url.startswith("http"):
        url = StorageService.get_public_url(asset.file_url)
    else:
        url = asset.file_url
    return RedirectResponse(url=url)


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


@router.post("/assets/batch-upload", response_model=ApiResponse[dict])
async def batch_upload_assets(
    request: BatchUploadAssetsRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """批量上传素材到电商平台"""
    service = AssetUploadService(db, tenant_id)
    results = {"success": [], "failed": []}

    for asset_id in request.asset_ids:
        try:
            platform_url = await service.upload_to_platform(
                asset_id=asset_id,
                platform_config_id=request.platform_config_id,
            )
            results["success"].append({"asset_id": asset_id, "platform_url": platform_url})
        except Exception as e:
            results["failed"].append({"asset_id": asset_id, "error": str(e)})

    return ApiResponse(data=results)

