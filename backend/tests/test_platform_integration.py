"""平台对接集成测试

测试场景：
1. AdapterRegistry 所有5个平台都已注册
2. 各适配器 get_auth_url() 返回正确的授权 URL
3. DTO 转换正确性
4. 事件解析正确性
5. PlatformType 枚举覆盖
"""
import pytest
from datetime import datetime

# 确保所有适配器被导入并注册
import services.platform.pdd_adapter  # noqa: F401
import services.platform.douyin_adapter  # noqa: F401
import services.platform.taobao.adapter  # noqa: F401
import services.platform.jd.adapter  # noqa: F401
import services.platform.kuaishou.adapter  # noqa: F401

from services.platform.adapter_registry import _adapters, get_supported_platforms, create_adapter
from services.platform.dto import (
    PlatformType,
    EventType,
    AfterSaleType,
    AfterSaleStatus,
    AuthorizationStatus,
    ProductDTO,
    OrderDTO,
    PageResult,
    TokenResult,
    AfterSaleDTO,
    PlatformEvent,
    MessageEvent,
    OrderEvent,
    AfterSaleEvent,
)


# ===== 1. AdapterRegistry 全平台注册 =====

class TestAdapterRegistryAllPlatforms:
    """验证所有5个平台适配器都已正确注册"""

    ALL_PLATFORMS = ["pinduoduo", "douyin", "taobao", "jd", "kuaishou"]

    def test_all_five_platforms_registered(self):
        for pt in self.ALL_PLATFORMS:
            assert pt in _adapters, f"平台 {pt} 未注册"

    def test_get_supported_platforms_complete(self):
        supported = get_supported_platforms()
        for pt in self.ALL_PLATFORMS:
            assert pt in supported

    def test_adapter_count(self):
        assert len(_adapters) >= 5

    def test_each_adapter_is_subclass_of_base(self):
        from services.platform.base_adapter import BasePlatformAdapter
        for pt, cls in _adapters.items():
            assert issubclass(cls, BasePlatformAdapter), f"{pt} 适配器不是 BasePlatformAdapter 子类"


# ===== 2. 各适配器 get_auth_url =====

class TestAdapterAuthUrl:
    """验证各平台 get_auth_url() 返回正确的授权 URL"""

    @pytest.fixture
    def make_adapter(self):
        """工厂方法创建适配器实例（绕过 PlatformConfig 依赖）"""
        def _make(platform_type: str):
            cls = _adapters[platform_type]
            return cls(app_key="test_key", app_secret="test_secret", access_token="test_token")
        return _make

    def test_pdd_auth_url(self, make_adapter):
        adapter = make_adapter("pinduoduo")
        url = adapter.get_auth_url("https://example.com/callback", "test_state")
        assert "pinduoduo.com" in url
        assert "test_key" in url

    def test_douyin_auth_url(self, make_adapter):
        adapter = make_adapter("douyin")
        url = adapter.get_auth_url("https://example.com/callback", "test_state")
        assert "douyin" in url.lower() or "jinritemai" in url.lower() or "toutiao" in url.lower()
        assert "test_key" in url

    def test_taobao_auth_url(self, make_adapter):
        adapter = make_adapter("taobao")
        url = adapter.get_auth_url("https://example.com/callback", "test_state")
        assert "taobao" in url.lower()
        assert "test_key" in url

    def test_jd_auth_url(self, make_adapter):
        adapter = make_adapter("jd")
        url = adapter.get_auth_url("https://example.com/callback", "test_state")
        assert "jd" in url.lower() or "jingdong" in url.lower()
        assert "test_key" in url

    def test_kuaishou_auth_url(self, make_adapter):
        adapter = make_adapter("kuaishou")
        url = adapter.get_auth_url("https://example.com/callback", "test_state")
        assert "kuaishou" in url.lower()
        assert "test_key" in url


# ===== 3. DTO 转换正确性 =====

class TestDTOConversion:
    """验证 DTO 数据类实例化和字段正确性"""

    def test_product_dto_defaults(self):
        p = ProductDTO(platform_product_id="P001", title="测试商品", price=99.9)
        assert p.platform_product_id == "P001"
        assert p.title == "测试商品"
        assert p.price == 99.9
        assert p.images == []
        assert p.sales_count == 0
        assert p.status == "active"

    def test_product_dto_full(self):
        p = ProductDTO(
            platform_product_id="P002",
            title="完整商品",
            price=199.0,
            original_price=299.0,
            description="详细描述",
            category="电子产品",
            images=["img1.jpg", "img2.jpg"],
            videos=["v1.mp4"],
            attributes={"color": "red"},
            sales_count=100,
            stock=50,
            status="inactive",
            platform_data={"raw": True},
        )
        assert p.original_price == 299.0
        assert len(p.images) == 2
        assert p.attributes["color"] == "red"

    def test_order_dto_defaults(self):
        o = OrderDTO(platform_order_id="ORD001")
        assert o.platform_order_id == "ORD001"
        assert o.quantity == 1
        assert o.status == "pending"
        assert o.paid_at is None

    def test_token_result(self):
        t = TokenResult(
            access_token="at_123",
            refresh_token="rt_456",
            expires_in=3600,
            shop_id="shop_789",
            shop_name="测试店铺",
        )
        assert t.access_token == "at_123"
        assert t.shop_name == "测试店铺"

    def test_aftersale_dto(self):
        a = AfterSaleDTO(
            platform_aftersale_id="AS001",
            order_id="ORD001",
            aftersale_type="return_refund",
            refund_amount=50.0,
            buyer_id="buyer_123",
        )
        assert a.aftersale_type == "return_refund"
        assert a.refund_amount == 50.0

    def test_page_result(self):
        pr = PageResult(items=["a", "b", "c"], total=100, page=1, page_size=20)
        assert len(pr.items) == 3
        assert pr.total == 100


# ===== 4. 事件解析正确性 =====

class TestEventModels:
    """验证事件模型实例化和继承正确性"""

    def test_platform_event_base(self):
        e = PlatformEvent(
            event_type="message",
            platform_type="pinduoduo",
            shop_id="shop_001",
            event_id="evt_001",
        )
        assert e.event_type == "message"
        assert isinstance(e.timestamp, datetime)
        assert e.raw_data == {}

    def test_message_event_inherits_platform_event(self):
        me = MessageEvent(
            event_type="message",
            platform_type="douyin",
            shop_id="shop_002",
            buyer_id="buyer_abc",
            conversation_id="conv_123",
            content="你好，有什么可以帮助的？",
            msg_type="text",
        )
        assert isinstance(me, PlatformEvent)
        assert me.buyer_id == "buyer_abc"
        assert me.content == "你好，有什么可以帮助的？"
        assert me.platform_type == "douyin"

    def test_order_event(self):
        oe = OrderEvent(
            event_type="order_status",
            platform_type="taobao",
            shop_id="shop_003",
            order_id="ord_789",
            old_status="paid",
            new_status="shipped",
        )
        assert isinstance(oe, PlatformEvent)
        assert oe.old_status == "paid"
        assert oe.new_status == "shipped"

    def test_aftersale_event(self):
        ae = AfterSaleEvent(
            event_type="aftersale",
            platform_type="jd",
            shop_id="shop_004",
            aftersale_id="as_001",
            order_id="ord_001",
            aftersale_type="refund_only",
            status="pending",
        )
        assert isinstance(ae, PlatformEvent)
        assert ae.aftersale_type == "refund_only"


# ===== 5. PlatformType 枚举覆盖 =====

class TestEnums:
    """验证所有枚举值覆盖"""

    def test_platform_type_values(self):
        assert PlatformType.PINDUODUO.value == "pinduoduo"
        assert PlatformType.DOUYIN.value == "douyin"
        assert PlatformType.TAOBAO.value == "taobao"
        assert PlatformType.JD.value == "jd"
        assert PlatformType.KUAISHOU.value == "kuaishou"
        assert len(PlatformType) == 5

    def test_event_type_values(self):
        assert EventType.MESSAGE.value == "message"
        assert EventType.ORDER_STATUS.value == "order_status"
        assert EventType.AFTERSALE.value == "aftersale"
        assert EventType.PRODUCT_CHANGE.value == "product_change"

    def test_aftersale_type_values(self):
        assert AfterSaleType.REFUND_ONLY.value == "refund_only"
        assert AfterSaleType.RETURN_REFUND.value == "return_refund"
        assert AfterSaleType.EXCHANGE.value == "exchange"

    def test_aftersale_status_values(self):
        assert len(AfterSaleStatus) == 6

    def test_authorization_status_values(self):
        assert AuthorizationStatus.PENDING.value == "pending"
        assert AuthorizationStatus.AUTHORIZED.value == "authorized"
        assert AuthorizationStatus.EXPIRED.value == "expired"
        assert AuthorizationStatus.REVOKED.value == "revoked"
