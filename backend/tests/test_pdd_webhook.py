import pytest
import hashlib
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def make_signature(token: str, body: bytes) -> str:
    return hashlib.md5(token.encode() + body).hexdigest()


def test_webhook_invalid_signature():
    """签名错误应返回 403"""
    with patch("api.routers.pdd_webhook.channel") as mock_channel:
        mock_channel.verify_signature.return_value = False
        from api.main import app
        client = TestClient(app)
        response = client.post(
            "/api/v1/pdd/webhook",
            content=b'{"type":"IM_NEW_MESSAGE"}',
            headers={"X-Pdd-Sign": "wrong_sign"},
        )
    assert response.status_code == 403


def test_webhook_non_message_event():
    """非消息事件应返回 200 但不处理"""
    with patch("api.routers.pdd_webhook.channel") as mock_channel:
        mock_channel.verify_signature.return_value = True
        mock_channel.parse_message.return_value = None  # non-message event
        from api.main import app
        client = TestClient(app)
        body = json.dumps({"type": "ORDER_PAID", "data": {}}).encode()
        response = client.post(
            "/api/v1/pdd/webhook",
            content=body,
            headers={"X-Pdd-Sign": "any_sign"},
        )
    assert response.status_code == 200
    assert response.json() == {"success": True}
