"""
API 路由模块
"""
from api.routers import admin, ai_chat, conversation, intent, knowledge, payment, rag, tenant, websocket

__all__ = [
    "admin",
    "tenant",
    "conversation",
    "knowledge",
    "payment",
    "ai_chat",
    "websocket",
    "intent",
    "rag",
]
