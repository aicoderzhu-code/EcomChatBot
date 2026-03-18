"""平台对接统一网关路由

将所有平台的 OAuth / Webhook / Reply 统一为参数化路由：
  /platform/{platform_type}/auth
  /platform/{platform_type}/callback
  /platform/{platform_type}/webhook
  /platform/{platform_type}/reply
"""
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import and_, select

from api.dependencies import DBDep, TenantTokenDep
from core.crypto import decrypt_field, encrypt_field
from models.platform import PlatformConfig
from models.platform_app import PlatformApp
from models.webhook_event import WebhookEvent
from schemas.platform import PlatformConfigResponse
from services.platform.adapter_registry import create_adapter, get_supported_platforms

# 确保所有适配器被注册
import services.platform.pdd_adapter  # noqa: F401
import services.platform.douyin_adapter  # noqa: F401
import services.platform.taobao.adapter  # noqa: F401
import services.platform.jd.adapter  # noqa: F401
import services.platform.kuaishou.adapter  # noqa: F401

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["平台对接"])


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _get_platform_app(db, platform_type: str) -> PlatformApp:
    """获取 ISV 应用配置"""
    stmt = select(PlatformApp).where(
        and_(
            PlatformApp.platform_type == platform_type,
            PlatformApp.status == "active",
        )
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail=f"未配置 {platform_type} ISV 应用")
    return app


async def _get_config_by_id(db, config_id: int, tenant_id: str) -> PlatformConfig:
    """根据 ID 获取平台配置"""
    stmt = select(PlatformConfig).where(
        and_(
            PlatformConfig.id == config_id,
            PlatformConfig.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


async def _find_config_by_shop(db, platform_type: str, shop_id: str) -> PlatformConfig | None:
    """根据 shop_id 查找配置"""
    stmt = select(PlatformConfig).where(
        and_(
            PlatformConfig.platform_type == platform_type,
            PlatformConfig.shop_id == shop_id,
            PlatformConfig.is_active == True,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Webhook（无需认证）
# ---------------------------------------------------------------------------

@router.post("/{platform_type}/webhook", summary="统一 Webhook 接收", include_in_schema=False)
async def unified_webhook(
    platform_type: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBDep,
):
    """统一接收各平台 Webhook 推送

    流程：
    1. 获取 ISV 应用配置
    2. 创建适配器验证签名
    3. 解析事件
    4. 持久化到 webhook_events 表
    5. 异步分发处理
    """
    if platform_type not in get_supported_platforms():
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform_type}")

    body = await request.body()
    try:
        payload_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的请求体")

    # 获取 ISV 应用
    app = await _get_platform_app(db, platform_type)

    # 创建适配器用于验签和事件解析
    try:
        app_secret = decrypt_field(app.app_secret)
    except Exception:
        app_secret = app.app_secret

    from services.platform.adapter_registry import _adapters
    adapter_cls = _adapters.get(platform_type)
    if not adapter_cls:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform_type}")

    adapter = adapter_cls(
        app_key=app.app_key,
        app_secret=app_secret,
        access_token=None,
    )

    # 验签
    headers_dict = dict(request.headers)
    if not adapter.verify_webhook(headers_dict, body):
        raise HTTPException(status_code=401, detail="Webhook 签名验证失败")

    # 解析事件
    events = adapter.parse_webhook_event(payload_data)

    # 持久化事件并异步处理
    for event in events:
        event_id = event.event_id or str(uuid.uuid4())

        # 幂等检查
        existing = await db.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        if existing.scalar_one_or_none():
            continue

        # 查找对应的商家配置
        config = await _find_config_by_shop(db, platform_type, event.shop_id)

        webhook_event = WebhookEvent(
            tenant_id=config.tenant_id if config else "unknown",
            event_id=event_id,
            platform_type=platform_type,
            platform_config_id=config.id if config else None,
            event_type=event.event_type,
            payload=event.raw_data,
            status="received",
        )
        db.add(webhook_event)

    await db.commit()

    # 异步处理（兼容现有的 PlatformMessageService）
    from services.platform.platform_message_service import PlatformMessageService
    service = PlatformMessageService(db)
    if platform_type == "pinduoduo":
        background_tasks.add_task(service.handle_pinduoduo_webhook, payload_data)
    elif platform_type == "douyin":
        background_tasks.add_task(service.handle_douyin_webhook, payload_data)
    elif platform_type == "kuaishou":
        # ⚠️ 快手 IM 消息推送尚未实测，字段格式待注册 ISV 账号后验证
        background_tasks.add_task(service.handle_kuaishou_webhook, payload_data)

    # 快速响应
    if platform_type == "douyin":
        return {"code": 0, "msg": "success"}
    return {"success": True}


# ---------------------------------------------------------------------------
# OAuth 授权（JWT 认证）
# ---------------------------------------------------------------------------

@router.get("/{platform_type}/auth", summary="跳转平台 OAuth 授权")
async def oauth_redirect(
    platform_type: str,
    tenant_id: TenantTokenDep,
    db: DBDep,
    redirect_uri: str,
    config_id: int | None = None,
):
    """通用 OAuth 授权跳转

    如果 config_id 存在，使用已有配置；否则自动创建新配置。
    """
    if platform_type not in get_supported_platforms():
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform_type}")

    app = await _get_platform_app(db, platform_type)

    if config_id:
        config = await _get_config_by_id(db, config_id, tenant_id)
    else:
        # 自动创建平台配置
        config = PlatformConfig(
            tenant_id=tenant_id,
            platform_type=platform_type,
            app_key=app.app_key,
            app_secret=app.app_secret,
            platform_app_id=app.id,
            is_active=False,
            authorization_status="pending",
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    # 使用适配器生成授权 URL
    adapter = create_adapter(config, app)
    state = f"{tenant_id}:{config.id}"
    auth_url = adapter.get_auth_url(state=state, redirect_uri=redirect_uri)

    return RedirectResponse(url=auth_url)


@router.get("/{platform_type}/callback", summary="OAuth 回调", include_in_schema=False)
async def oauth_callback(
    platform_type: str,
    code: str,
    state: str,
    db: DBDep,
):
    """通用 OAuth 回调处理"""
    parts = state.split(":")
    if len(parts) != 2:
        return RedirectResponse(url="/settings?menu=platform&status=error&msg=invalid_state")

    tenant_id, config_id = parts[0], int(parts[1])

    stmt = select(PlatformConfig).where(
        and_(
            PlatformConfig.id == config_id,
            PlatformConfig.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return RedirectResponse(url="/settings?menu=platform&status=error&msg=no_config")

    # 获取 ISV 应用
    app = await _get_platform_app(db, platform_type)
    adapter = create_adapter(config, app)

    try:
        token_result = await adapter.exchange_token(code)
    except Exception as e:
        logger.error("换取 access_token 失败: %s", e)
        return RedirectResponse(url="/settings?menu=platform&status=error&msg=token_failed")

    # 更新配置
    config.access_token = token_result.access_token
    config.refresh_token = token_result.refresh_token
    config.expires_at = datetime.utcnow() + timedelta(seconds=token_result.expires_in)
    config.token_expires_at = config.expires_at
    config.shop_id = token_result.shop_id or config.shop_id
    if token_result.shop_name:
        config.shop_name = token_result.shop_name
    config.is_active = True
    config.authorization_status = "authorized"
    config.last_token_refresh = datetime.utcnow()

    await db.commit()

    return RedirectResponse(url="/settings?menu=platform&status=success")


# ---------------------------------------------------------------------------
# 平台配置 CRUD（JWT 认证）
# ---------------------------------------------------------------------------

@router.get("/configs", summary="获取所有平台配置", response_model=list[PlatformConfigResponse])
async def get_platform_configs(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取当前租户的所有平台配置"""
    stmt = select(PlatformConfig).where(PlatformConfig.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/apps", summary="获取可用的 ISV 应用列表")
async def get_platform_apps(
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """获取所有已配置的 ISV 应用"""
    stmt = select(PlatformApp).where(PlatformApp.status == "active")
    result = await db.execute(stmt)
    apps = result.scalars().all()
    return [
        {
            "platform_type": a.platform_type,
            "app_name": a.app_name,
            "status": a.status,
        }
        for a in apps
    ]


@router.delete("/configs/{config_id}", summary="断开平台连接")
async def disconnect_platform(
    tenant_id: TenantTokenDep,
    db: DBDep,
    config_id: int,
):
    """断开平台授权"""
    config = await _get_config_by_id(db, config_id, tenant_id)
    config.access_token = None
    config.refresh_token = None
    config.expires_at = None
    config.is_active = False
    config.authorization_status = "revoked"
    await db.commit()
    return {"success": True, "message": f"已断开 {config.platform_type} 连接"}


# ---------------------------------------------------------------------------
# 人工回复（JWT 认证）
# ---------------------------------------------------------------------------

class ManualReplyRequest(BaseModel):
    conversation_id: str
    content: str


@router.post("/{platform_type}/reply", summary="人工回复消息")
async def manual_reply(
    platform_type: str,
    tenant_id: TenantTokenDep,
    db: DBDep,
    body: ManualReplyRequest,
):
    """通用人工回复"""
    from models import Conversation, Message

    # 查找会话
    stmt = select(Conversation).where(
        and_(
            Conversation.tenant_id == tenant_id,
            Conversation.conversation_id == body.conversation_id,
            Conversation.platform_type == platform_type,
        )
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 查找平台配置
    stmt2 = select(PlatformConfig).where(
        and_(
            PlatformConfig.tenant_id == tenant_id,
            PlatformConfig.platform_type == platform_type,
            PlatformConfig.is_active == True,
        )
    )
    result2 = await db.execute(stmt2)
    config = result2.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=400, detail="平台未连接")

    app = await _get_platform_app(db, platform_type)
    adapter = create_adapter(config, app)

    try:
        await adapter.send_message(
            conversation_id=conversation.platform_conversation_id,
            content=body.content,
        )
    except Exception as e:
        logger.error("人工回复发送失败: %s", e)
        raise HTTPException(status_code=502, detail="消息发送失败")

    # 保存消息记录
    msg = Message(
        tenant_id=tenant_id,
        message_id=f"msg_{int(datetime.utcnow().timestamp())}_{platform_type}_human",
        conversation_id=body.conversation_id,
        role="assistant",
        content=body.content,
    )
    db.add(msg)
    await db.commit()

    return {"success": True}
