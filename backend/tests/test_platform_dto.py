"""DTO 和事件模型测试"""
from services.platform.dto import (
    PlatformType, EventType, AfterSaleType, AuthorizationStatus,
    ProductDTO, OrderDTO, PageResult, TokenResult, AfterSaleDTO,
    PlatformEvent, MessageEvent, OrderEvent, AfterSaleEvent,
)


def test_platform_type_enum():
    assert PlatformType.PINDUODUO.value == "pinduoduo"
    assert PlatformType.TAOBAO.value == "taobao"
    assert PlatformType.JD.value == "jd"
    assert PlatformType.KUAISHOU.value == "kuaishou"


def test_token_result():
    result = TokenResult(
        access_token="token123",
        refresh_token="refresh456",
        expires_in=3600,
        shop_id="shop1",
    )
    assert result.access_token == "token123"
    assert result.shop_id == "shop1"


def test_aftersale_dto():
    dto = AfterSaleDTO(
        platform_aftersale_id="as001",
        order_id="order001",
        aftersale_type="refund_only",
        refund_amount=99.9,
    )
    assert dto.platform_aftersale_id == "as001"
    assert dto.refund_amount == 99.9


def test_message_event():
    event = MessageEvent(
        event_type=EventType.MESSAGE.value,
        platform_type=PlatformType.PINDUODUO.value,
        shop_id="shop1",
        buyer_id="buyer1",
        conversation_id="conv1",
        content="你好",
    )
    assert event.event_type == "message"
    assert event.buyer_id == "buyer1"


def test_page_result():
    result = PageResult(items=[1, 2, 3], total=10, page=1, page_size=3)
    assert len(result.items) == 3
    assert result.total == 10
