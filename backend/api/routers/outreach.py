"""外呼活动 + 自动规则 API 路由"""
from fastapi import APIRouter, Query

from api.dependencies import DBDep, TenantFlexDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.outreach import (
    CampaignCreateRequest,
    CampaignResponse,
    CampaignStatsResponse,
    CampaignUpdateRequest,
    OutreachTaskResponse,
    RuleCreateRequest,
    RuleResponse,
    RuleUpdateRequest,
)
from services.outreach_service import OutreachService
from services.outreach_rule_service import OutreachRuleService

router = APIRouter(prefix="/outreach", tags=["智能触达"])


# ===== 活动管理 =====

@router.post("/campaigns", response_model=ApiResponse[CampaignResponse])
async def create_campaign(
    request: CampaignCreateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建外呼活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.create_campaign(**request.model_dump())
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.get("/campaigns", response_model=ApiResponse[PaginatedResponse[CampaignResponse]])
async def list_campaigns(
    tenant_id: TenantFlexDep,
    db: DBDep,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """活动列表"""
    service = OutreachService(db, tenant_id)
    campaigns, total = await service.list_campaigns(status=status, page=page, size=size)
    items = [CampaignResponse.model_validate(c) for c in campaigns]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/campaigns/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def get_campaign(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """活动详情"""
    service = OutreachService(db, tenant_id)
    campaign = await service.get_campaign_detail(campaign_id)
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.put("/campaigns/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.update_campaign(campaign_id, **request.model_dump(exclude_unset=True))
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.post("/campaigns/{campaign_id}/launch", response_model=ApiResponse[CampaignResponse])
async def launch_campaign(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """启动活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.launch_campaign(campaign_id)
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.post("/campaigns/{campaign_id}/pause", response_model=ApiResponse[CampaignResponse])
async def pause_campaign(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """暂停活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.pause_campaign(campaign_id)
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.post("/campaigns/{campaign_id}/resume", response_model=ApiResponse[CampaignResponse])
async def resume_campaign(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """恢复活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.resume_campaign(campaign_id)
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.post("/campaigns/{campaign_id}/cancel", response_model=ApiResponse[CampaignResponse])
async def cancel_campaign(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """取消活动"""
    service = OutreachService(db, tenant_id)
    campaign = await service.cancel_campaign(campaign_id)
    return ApiResponse(data=CampaignResponse.model_validate(campaign))


@router.get("/campaigns/{campaign_id}/tasks", response_model=ApiResponse[PaginatedResponse[OutreachTaskResponse]])
async def get_campaign_tasks(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """活动任务列表"""
    service = OutreachService(db, tenant_id)
    tasks, total = await service.get_campaign_tasks(campaign_id, status=status, page=page, size=size)
    items = [OutreachTaskResponse.model_validate(t) for t in tasks]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/campaigns/{campaign_id}/stats", response_model=ApiResponse[CampaignStatsResponse])
async def get_campaign_stats(
    campaign_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """活动统计"""
    service = OutreachService(db, tenant_id)
    stats = await service.get_campaign_stats(campaign_id)
    return ApiResponse(data=stats)


# ===== 自动规则 =====

@router.post("/rules", response_model=ApiResponse[RuleResponse])
async def create_rule(
    request: RuleCreateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建自动规则"""
    service = OutreachRuleService(db, tenant_id)
    rule = await service.create_rule(**request.model_dump())
    return ApiResponse(data=RuleResponse.model_validate(rule))


@router.get("/rules", response_model=ApiResponse[PaginatedResponse[RuleResponse]])
async def list_rules(
    tenant_id: TenantFlexDep,
    db: DBDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """规则列表"""
    service = OutreachRuleService(db, tenant_id)
    rules, total = await service.list_rules(page=page, size=size)
    items = [RuleResponse.model_validate(r) for r in rules]
    return ApiResponse(data=PaginatedResponse.create(items=items, total=total, page=page, size=size))


@router.get("/rules/{rule_id}", response_model=ApiResponse[RuleResponse])
async def get_rule(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """规则详情"""
    service = OutreachRuleService(db, tenant_id)
    rule = await service._get_rule(rule_id)
    return ApiResponse(data=RuleResponse.model_validate(rule))


@router.put("/rules/{rule_id}", response_model=ApiResponse[RuleResponse])
async def update_rule(
    rule_id: int,
    request: RuleUpdateRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新规则"""
    service = OutreachRuleService(db, tenant_id)
    rule = await service.update_rule(rule_id, **request.model_dump(exclude_unset=True))
    return ApiResponse(data=RuleResponse.model_validate(rule))


@router.delete("/rules/{rule_id}", response_model=ApiResponse)
async def delete_rule(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除规则"""
    service = OutreachRuleService(db, tenant_id)
    await service.delete_rule(rule_id)
    return ApiResponse(data={"message": "删除成功"})


@router.post("/rules/{rule_id}/toggle", response_model=ApiResponse[RuleResponse])
async def toggle_rule(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """启用/禁用规则"""
    service = OutreachRuleService(db, tenant_id)
    rule = await service.toggle_rule(rule_id)
    return ApiResponse(data=RuleResponse.model_validate(rule))


@router.get("/rules/{rule_id}/stats", response_model=ApiResponse)
async def get_rule_stats(
    rule_id: int,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """规则统计"""
    service = OutreachRuleService(db, tenant_id)
    stats = await service.get_rule_stats(rule_id)
    return ApiResponse(data=stats)
