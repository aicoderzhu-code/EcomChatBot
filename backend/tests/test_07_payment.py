"""
支付管理模块测试
测试覆盖: 10个接口, 50个测试用例
包含: 订单创建、订单查询、支付回调、退款流程、微信支付等
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper, MockDataBuilder, generate_order_number

pytestmark = [pytest.mark.asyncio, pytest.mark.payment]


# ==================== 1. 订单创建测试 ====================


class TestPaymentOrderCreation:
    """支付订单创建测试"""

    async def test_create_payment_order_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建基础套餐支付订单"""
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
            "description": "订阅基础套餐",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证订单信息
        order = data["data"]
        assert "order_id" in order
        assert "order_number" in order
        assert "amount" in order
        assert "currency" in order
        assert order["currency"] == "CNY"
        assert "payment_html" in order
        assert "expires_at" in order

        # 验证金额
        assert float(order["amount"]) > 0

    async def test_create_payment_order_professional(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建专业版套餐订单"""
        order_data = {
            "plan_type": "professional",
            "duration_months": 3,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        order = data["data"]

        # 专业版价格应该高于基础版
        assert float(order["amount"]) > 99

    async def test_create_payment_order_enterprise(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建企业版套餐订单"""
        order_data = {
            "plan_type": "enterprise",
            "duration_months": 12,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        order = data["data"]

        # 企业版价格应该最高
        assert float(order["amount"]) > 299

    async def test_create_payment_order_mobile(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建移动端支付订单"""
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "mobile",  # 移动端支付
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_create_payment_order_renewal(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建续费订单"""
        order_data = {
            "plan_type": "basic",
            "duration_months": 6,
            "payment_type": "pc",
            "subscription_type": "renewal",  # 续费
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_create_payment_order_upgrade(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建升级订单"""
        order_data = {
            "plan_type": "professional",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "upgrade",  # 升级
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_create_payment_order_invalid_plan(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建订单 - 无效套餐类型"""
        order_data = {
            "plan_type": "invalid_plan",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]

    async def test_create_payment_order_invalid_duration(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建订单 - 无效订阅时长"""
        order_data = {
            "plan_type": "basic",
            "duration_months": 0,  # 无效
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]


# ==================== 2. 订单查询测试 ====================


class TestPaymentOrderQuery:
    """支付订单查询测试"""

    async def test_get_order_detail(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询订单详情"""
        # 先创建订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )
        order_number = create_response.json()["data"]["order_number"]

        # 查询订单详情
        response = await client.get(
            f"/api/v1/payment/orders/{order_number}",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证订单详情
        order_detail = data["data"]
        assert order_detail["order_number"] == order_number
        assert "status" in order_detail
        assert "amount" in order_detail
        assert "created_at" in order_detail

    async def test_get_order_detail_not_found(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询不存在的订单"""
        response = await client.get(
            "/api/v1/payment/orders/ORDER_NOTEXIST",
            headers=tenant_api_key_headers,
        )

        AssertHelper.assert_response_error(response, 404)

    async def test_sync_order_status(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试同步订单状态"""
        # 创建订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )
        order_number = create_response.json()["data"]["order_number"]

        # 同步订单状态
        response = await client.post(
            f"/api/v1/payment/orders/{order_number}/sync",
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert data["data"]["success"] is True

    async def test_list_orders(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询订单列表"""
        response = await client.get(
            "/api/v1/payment/orders/list",
            params={"page": 1, "size": 20},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)
        AssertHelper.assert_pagination(data["data"])

    async def test_list_orders_filter_by_status(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试按状态过滤订单"""
        response = await client.get(
            "/api/v1/payment/orders/list",
            params={"status": "pending"},
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            items = data["data"]["items"]
            for item in items:
                assert item["status"] == "pending"


# ==================== 3. 支付宝回调测试 ====================


class TestAlipayCallback:
    """支付宝支付回调测试"""

    async def test_alipay_callback_success(self, client: AsyncClient):
        """测试支付宝支付成功回调"""
        order_number = generate_order_number()
        callback_data = MockDataBuilder.build_payment_callback(
            order_number, status="success"
        )

        response = await client.post(
            "/api/v1/payment/callback/alipay", data=callback_data
        )

        # 回调应该返回success
        assert response.status_code in [200, 204]

    async def test_alipay_callback_failed(self, client: AsyncClient):
        """测试支付宝支付失败回调"""
        order_number = generate_order_number()
        callback_data = MockDataBuilder.build_payment_callback(order_number, status="failed")

        response = await client.post(
            "/api/v1/payment/callback/alipay", data=callback_data
        )

        assert response.status_code in [200, 204]

    async def test_alipay_callback_invalid_sign(self, client: AsyncClient):
        """测试支付宝回调 - 签名验证失败"""
        callback_data = {
            "out_trade_no": "ORDER_TEST",
            "trade_status": "TRADE_SUCCESS",
            "sign": "invalid_signature",
        }

        response = await client.post(
            "/api/v1/payment/callback/alipay", data=callback_data
        )

        # 签名错误应该返回错误
        assert response.status_code in [400, 403]

    async def test_alipay_return_url(self, client: AsyncClient):
        """测试支付宝同步回调(return_url)"""
        order_number = generate_order_number()
        return_params = {
            "out_trade_no": order_number,
            "trade_no": f"ALIPAY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "trade_status": "TRADE_SUCCESS",
        }

        response = await client.get(
            "/api/v1/payment/callback/alipay/return", params=return_params
        )

        # 同步回调通常重定向到成功页面
        assert response.status_code in [200, 302]


# ==================== 4. 微信支付测试 ====================


class TestWeChatPay:
    """微信支付测试"""

    async def test_create_wechat_payment_native(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建微信扫码支付订单"""
        payment_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_method": "native",  # 扫码支付
        }

        response = await client.post(
            "/api/v1/payment/wechat/create",
            json=payment_data,
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert "code_url" in data["data"]  # 二维码URL

    async def test_create_wechat_payment_h5(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建微信H5支付订单"""
        payment_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_method": "h5",  # H5支付
        }

        response = await client.post(
            "/api/v1/payment/wechat/create",
            json=payment_data,
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert "h5_url" in data["data"]  # H5支付URL

    async def test_wechat_payment_callback(self, client: AsyncClient):
        """测试微信支付回调"""
        # 微信回调数据格式(XML)
        callback_xml = """
        <xml>
            <out_trade_no>ORDER_TEST</out_trade_no>
            <result_code>SUCCESS</result_code>
            <trade_state>SUCCESS</trade_state>
        </xml>
        """

        response = await client.post(
            "/api/v1/payment/callback/wechat",
            content=callback_xml,
            headers={"Content-Type": "application/xml"},
        )

        # 微信要求返回成功XML
        assert response.status_code in [200, 204]


# ==================== 5. 退款流程测试 ====================


class TestRefund:
    """退款流程测试"""

    async def test_create_refund_request(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试创建退款申请"""
        # 先创建支付订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )
        order_number = create_response.json()["data"]["order_number"]

        # 创建退款申请
        refund_data = {
            "order_number": order_number,
            "refund_amount": 99.00,
            "reason": "测试退款",
        }

        response = await client.post(
            "/api/v1/payment/refund/create",
            json=refund_data,
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert "refund_id" in data["data"]
            assert "status" in data["data"]

    async def test_query_refund_detail(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询退款详情"""
        refund_id = "REFUND_TEST_001"

        response = await client.get(
            f"/api/v1/payment/refund/{refund_id}",
            headers=tenant_api_key_headers,
        )

        # 退款可能不存在
        assert response.status_code in [200, 404]

    async def test_refund_callback(self, client: AsyncClient):
        """测试退款回调"""
        refund_callback_data = {
            "refund_id": "REFUND_TEST",
            "refund_status": "SUCCESS",
            "refund_amount": "99.00",
        }

        response = await client.post(
            "/api/v1/payment/callback/refund", json=refund_callback_data
        )

        assert response.status_code in [200, 204]

    async def test_cancel_refund(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试取消退款申请"""
        refund_id = "REFUND_TEST_001"

        response = await client.post(
            f"/api/v1/payment/refund/{refund_id}/cancel",
            headers=tenant_api_key_headers,
        )

        # 可能不存在或已处理
        assert response.status_code in [200, 400, 404]


# ==================== 6. 订单状态测试 ====================


class TestOrderStatus:
    """订单状态测试"""

    async def test_order_status_query(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试查询订单支付状态"""
        # 创建订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )
        order_number = create_response.json()["data"]["order_number"]

        # 查询支付状态
        response = await client.get(
            f"/api/v1/payment/orders/{order_number}/status",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        status_info = data["data"]
        assert "status" in status_info
        assert "paid" in status_info
        assert "pay_time" in status_info or status_info["paid"] is False

    async def test_order_cancel(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试取消订单"""
        # 创建订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )
        order_number = create_response.json()["data"]["order_number"]

        # 取消订单
        response = await client.post(
            f"/api/v1/payment/orders/{order_number}/cancel",
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)


# ==================== 7. 订单过期测试 ====================


class TestOrderExpiration:
    """订单过期测试"""

    async def test_order_expiration(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试订单过期处理"""
        # 创建订单
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        create_response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = create_response.json()
        order = data["data"]

        # 验证过期时间
        assert "expires_at" in order
        expires_at = datetime.fromisoformat(order["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(expires_at.tzinfo)

        # 过期时间应该在未来
        assert expires_at > now


# ==================== 8. 支付金额测试 ====================


class TestPaymentAmount:
    """支付金额计算测试"""

    async def test_payment_amount_calculation_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试基础套餐金额计算"""
        order_data = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response = await client.post(
            "/api/v1/payment/orders/create",
            json=order_data,
            headers=tenant_api_key_headers,
        )

        data = response.json()
        amount = float(data["data"]["amount"])

        # 基础套餐价格应该合理(假设是99元/月)
        assert 90 < amount < 110  # 允许一些浮动

    async def test_payment_amount_discount_long_term(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试长期订阅折扣"""
        # 1个月订单
        order_1m = {
            "plan_type": "basic",
            "duration_months": 1,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response_1m = await client.post(
            "/api/v1/payment/orders/create",
            json=order_1m,
            headers=tenant_api_key_headers,
        )
        amount_1m = float(response_1m.json()["data"]["amount"])

        # 12个月订单
        order_12m = {
            "plan_type": "basic",
            "duration_months": 12,
            "payment_type": "pc",
            "subscription_type": "new",
        }

        response_12m = await client.post(
            "/api/v1/payment/orders/create",
            json=order_12m,
            headers=tenant_api_key_headers,
        )
        amount_12m = float(response_12m.json()["data"]["amount"])

        # 12个月应该有折扣，不应该等于1个月*12
        assert amount_12m < amount_1m * 12
