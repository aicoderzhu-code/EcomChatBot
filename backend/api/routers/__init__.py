"""
API 路由模块
"""
from api.routers import admin, ai_chat, auth, conversation, intent, knowledge, payment, rag, tenant, websocket, monitor, quality, webhook, model_config, statistics, analytics

__all__ = [
    "admin",
    "auth",
    "tenant",
    "conversation",
    "knowledge",
    "payment",
    "ai_chat",
    "websocket",
    "intent",
    "rag",
    "monitor",
    "quality",
    "webhook",
    "model_config",
    "statistics",
    "analytics",
]
