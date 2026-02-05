"""
Webhook 事件定义
"""
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WebhookEventType(str, Enum):
    """Webhook 事件类型"""

    # 会话事件
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_CLOSED = "conversation.closed"

    # 消息事件
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"

    # 用户事件
    USER_CREATED = "user.created"

    # 订阅事件
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_EXPIRED = "subscription.expired"

    # 配额事件
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"


# 事件类型描述
EVENT_TYPE_DESCRIPTIONS = {
    WebhookEventType.CONVERSATION_CREATED: {
        "name": "会话创建",
        "description": "当新会话创建时触发",
    },
    WebhookEventType.CONVERSATION_CLOSED: {
        "name": "会话关闭",
        "description": "当会话关闭时触发",
    },
    WebhookEventType.MESSAGE_RECEIVED: {
        "name": "消息接收",
        "description": "当收到用户消息时触发",
    },
    WebhookEventType.MESSAGE_SENT: {
        "name": "消息发送",
        "description": "当AI发送消息时触发",
    },
    WebhookEventType.USER_CREATED: {
        "name": "用户创建",
        "description": "当新用户创建时触发",
    },
    WebhookEventType.SUBSCRIPTION_CREATED: {
        "name": "订阅创建",
        "description": "当新订阅创建时触发",
    },
    WebhookEventType.SUBSCRIPTION_UPDATED: {
        "name": "订阅更新",
        "description": "当订阅更新时触发",
    },
    WebhookEventType.SUBSCRIPTION_EXPIRED: {
        "name": "订阅过期",
        "description": "当订阅过期时触发",
    },
    WebhookEventType.QUOTA_WARNING: {
        "name": "配额警告",
        "description": "当配额使用达到警告阈值时触发（默认80%）",
    },
    WebhookEventType.QUOTA_EXCEEDED: {
        "name": "配额超限",
        "description": "当配额超出限制时触发",
    },
}


def generate_event_id() -> str:
    """生成事件唯一ID"""
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    random_part = secrets.token_hex(8)
    return f"evt_{timestamp}_{random_part}"


@dataclass
class WebhookEvent:
    """Webhook 事件"""

    event_type: WebhookEventType
    tenant_id: str
    data: dict[str, Any]
    event_id: str = field(default_factory=generate_event_id)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_payload(self) -> dict[str, Any]:
        """转换为 Webhook 请求负载"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


def get_event_type_info() -> list[dict[str, str]]:
    """获取所有事件类型信息"""
    result = []
    for event_type in WebhookEventType:
        info = EVENT_TYPE_DESCRIPTIONS.get(event_type, {})
        result.append({
            "value": event_type.value,
            "name": info.get("name", event_type.value),
            "description": info.get("description", ""),
        })
    return result
