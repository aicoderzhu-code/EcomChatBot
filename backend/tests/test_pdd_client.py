import pytest
import hashlib
from unittest.mock import patch, AsyncMock
from services.pdd_client import PddClient


def test_sign_generation():
    """验证签名算法正确"""
    client = PddClient(app_key="test_key", app_secret="test_secret")
    params = {"type": "pdd.service.message.push", "timestamp": "1700000000"}
    sign = client._generate_sign(params)
    assert isinstance(sign, str)
    assert len(sign) == 32  # MD5 hex
    assert sign == sign.upper()  # PDD requires uppercase MD5


def test_build_request_params():
    """验证请求参数构建"""
    client = PddClient(app_key="test_key", app_secret="test_secret")
    params = client._build_params("pdd.service.message.push", {"msg": "hello"})
    assert params["client_id"] == "test_key"
    assert params["type"] == "pdd.service.message.push"
    assert "sign" in params
    assert "timestamp" in params


@pytest.mark.asyncio
async def test_send_message_success():
    """验证发送消息调用"""
    client = PddClient(app_key="test_key", app_secret="test_secret")
    mock_response = {"result": {"is_success": True}}
    with patch.object(client, "_request", return_value=mock_response) as mock_req:
        result = await client.send_message(
            conversation_id="conv_123",
            content="您好，请问有什么可以帮您？",
            msg_type=1,
        )
        assert result is True
        mock_req.assert_called_once()
