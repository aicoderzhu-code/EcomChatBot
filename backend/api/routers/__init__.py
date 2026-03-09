"""
API 路由模块
"""
from api.routers import admin, ai_chat, auth, conversation, intent, knowledge, knowledge_extraction, payment, platform, qa, rag, tenant, websocket, monitor, quality, webhook, statistics, analytics, setup, order, analysis_report

__all__ = [
    "admin",
    "auth",
    "tenant",
    "conversation",
    "knowledge",
    "knowledge_extraction",
    "qa",
    "payment",
    "ai_chat",
    "websocket",
    "intent",
    "rag",
    "monitor",
    "quality",
    "webhook",
    "statistics",
    "analytics",
    "setup",
    "platform",
    "order",
    "analysis_report",
]
