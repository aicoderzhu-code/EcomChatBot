import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from services.pdd_channel import PddChannel
from services.pdd_client import PddClient
from services.pdd_session import PddSessionManager
from services.conversation_chain_service import simple_chat
from db.session import AsyncSessionLocal
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pdd", tags=["pdd"])

channel = PddChannel()
pdd_client = PddClient()
session_manager = PddSessionManager()


@router.post("/webhook")
async def pdd_webhook(request: Request, background_tasks: BackgroundTasks):
    """接收拼多多消息推送"""
    body = await request.body()
    signature = request.headers.get("X-Pdd-Sign", "")

    if not channel.verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    msg = channel.parse_message(payload)

    if msg is None:
        return {"success": True}

    background_tasks.add_task(handle_message, msg)
    return {"success": True}


async def handle_message(msg: dict) -> None:
    """后台处理消息：AI 回复或转人工"""
    conversation_id = msg["conversation_id"]
    content = msg["content"]
    tenant_id = settings.pdd_app_key or "pdd_default"

    # 1. 检查是否已在人工模式
    if await session_manager.is_human_mode(conversation_id):
        logger.info(f"[PDD] conv={conversation_id} 人工模式，跳过 AI")
        return

    # 2. 检测转人工关键词
    if channel.should_transfer_to_human(content):
        await session_manager.set_human_mode(conversation_id, True)
        await pdd_client.send_message(
            conversation_id,
            "好的，正在为您转接人工客服，请稍候～",
        )
        logger.info(f"[PDD] conv={conversation_id} 触发转人工")
        return

    # 3. 调用 AI 引擎生成回复
    try:
        async with AsyncSessionLocal() as db:
            result = await simple_chat(
                db=db,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_input=content,
            )
        reply = result.get("response", "")
        if reply:
            await pdd_client.send_message(conversation_id, reply)
            logger.info(f"[PDD] conv={conversation_id} AI 回复成功")
    except Exception as e:
        logger.error(f"[PDD] AI 回复失败: {e}")
        await pdd_client.send_message(
            conversation_id,
            "抱歉，系统繁忙，请稍后再试，或联系人工客服。",
        )
