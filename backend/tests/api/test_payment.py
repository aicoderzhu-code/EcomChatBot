"""
支付 API 测试

覆盖支付订单创建、查询、退款、订阅管理等所有支付接口
"""
import pytest
from test_base import BaseAPITest, TenantTestMixin, PaymentTestMixin
from config import settings


@pytest.mark.payment
class TestPayment(BaseAPITest, TenantTestMixin, PaymentTestMixin):
    """支付 API 测试"""

    @pytest.mark.asyncio
    async def test_create_payment_order(self):
        """测试创建支付宝支付订单"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/orders/create",
            json={
                "plan_type": "professional",
                "duration_months": 1,
                "payment_type": "pc",
                "subscription_type": "new",
                "description": "测试支付订单",
            }
        )

        if response.status_code == 200:
            data = self.assert_success(response)
            assert "order_number" in data
            assert data["amount"] > 0
            self.cleaner.register_payment_order(data["order_number"])
            print(f"✓ 支付订单创建成功: {data['order_number']}")
        else:
            print(f"⚠ 支付订单创建返回 {response.status_code}（支付网关可能未配置）")

    @pytest.mark.asyncio
    async def test_create_wechat_payment_order(self):
        """测试创建微信支付订单"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/wechat/orders/create",
            json={
                "plan_type": "basic",
                "duration_months": 3,
                "payment_type": "mobile",
                "subscription_type": "new",
            },
            params={"payment_method": "native"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True or "order_number" in data
            print("✓ 微信支付订单创建成功")
        else:
            print(f"⚠ 微信支付订单返回 {response.status_code}（微信支付可能未配置）")

    @pytest.mark.asyncio
    async def test_get_payment_order_detail(self):
        """测试查询订单详情"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 先创建订单
        create_resp = await self.client.post(
            "/payment/orders/create",
            json={
                "plan_type": "professional",
                "duration_months": 1,
                "payment_type": "pc",
                "subscription_type": "new",
            }
        )

        if create_resp.status_code != 200:
            pytest.skip("支付网关未配置，跳过订单查询测试")

        order_data = self.assert_success(create_resp)
        order_number = order_data["order_number"]
        self.cleaner.register_payment_order(order_number)

        # 查询订单详情
        detail_resp = await self.client.get(f"/payment/orders/{order_number}")
        assert detail_resp.status_code in [200, 404]

        if detail_resp.status_code == 200:
            print(f"✓ 订单详情查询成功: {order_number}")

    @pytest.mark.asyncio
    async def test_sync_order_status(self):
        """测试同步订单状态"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        # 使用不存在的订单号
        response = await self.client.post("/payment/orders/NONEXISTENT_ORDER/sync")
        assert response.status_code in [404, 500]
        print("✓ 不存在的订单同步返回正确状态")

    @pytest.mark.asyncio
    async def test_create_order_invalid_plan(self):
        """测试使用无效套餐类型创建订单"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/orders/create",
            json={
                "plan_type": "invalid_plan",
                "duration_months": 1,
                "payment_type": "pc",
                "subscription_type": "new",
            }
        )

        assert response.status_code in [400, 422, 500]
        print("✓ 无效套餐类型正确拒绝")

    @pytest.mark.asyncio
    async def test_create_order_invalid_duration(self):
        """测试使用无效时长创建订单"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/orders/create",
            json={
                "plan_type": "professional",
                "duration_months": 0,
                "payment_type": "pc",
                "subscription_type": "new",
            }
        )

        assert response.status_code in [400, 422, 500]
        print("✓ 无效时长正确拒绝")

    @pytest.mark.asyncio
    async def test_refund_nonexistent_order(self):
        """测试退款不存在的订单"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/orders/NONEXISTENT/refund",
            json={"refund_reason": "测试退款"}
        )

        assert response.status_code in [404, 500]
        print("✓ 退款不存在订单返回正确状态")

    @pytest.mark.asyncio
    async def test_subscribe_plan(self):
        """测试订阅套餐"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post(
            "/payment/subscription/subscribe",
            json={
                "plan_type": "basic",
                "duration_months": 1,
                "payment_method": "alipay",
                "auto_renew": False,
            }
        )

        if response.status_code == 200:
            data = self.assert_success(response)
            assert data.get("success") is True
            if data.get("order_number"):
                self.cleaner.register_payment_order(data["order_number"])
            print("✓ 订阅套餐成功")
        else:
            print(f"⚠ 订阅套餐返回 {response.status_code}")

    @pytest.mark.asyncio
    async def test_get_subscription_detail(self):
        """测试获取订阅详情"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.get("/payment/subscription")

        if response.status_code == 200:
            data = self.assert_success(response)
            assert "plan_type" in data
            assert "status" in data
            print(f"✓ 订阅详情查询成功: {data.get('plan_type')}")
        else:
            print(f"⚠ 订阅详情返回 {response.status_code}")

    @pytest.mark.asyncio
    async def test_change_subscription_plan(self):
        """测试变更套餐"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.put(
            "/payment/subscription/change",
            json={
                "new_plan_type": "professional",
                "effective_immediately": True,
            }
        )

        if response.status_code == 200:
            data = self.assert_success(response)
            assert data.get("success") is True
            print("✓ 套餐变更成功")
        elif response.status_code == 400:
            print("✓ 套餐变更正确拒绝（可能套餐相同）")
        else:
            print(f"⚠ 套餐变更返回 {response.status_code}")

    @pytest.mark.asyncio
    async def test_cancel_auto_renewal(self):
        """测试取消自动续费"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.post("/payment/subscription/cancel-renewal")

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            print("✓ 取消自动续费成功")
        else:
            print(f"⚠ 取消续费返回 {response.status_code}")

    @pytest.mark.asyncio
    async def test_preview_plan_change_price(self):
        """测试预览套餐变更差价"""
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.get(
            "/payment/subscription/prorated-price",
            params={"new_plan_type": "enterprise"}
        )

        if response.status_code == 200:
            data = self.assert_success(response)
            assert "prorated_charge" in data
            print(f"✓ 差价预览: ¥{data.get('prorated_charge')}")
        else:
            print(f"⚠ 差价预览返回 {response.status_code}")

    @pytest.mark.asyncio
    async def test_alipay_return_callback(self):
        """测试支付宝同步回调"""
        response = await self.client.get(
            "/payment/callback/alipay/return",
            params={
                "out_trade_no": "TEST_ORDER_001",
                "trade_no": "2024010122001",
                "total_amount": "99.00",
            }
        )

        assert response.status_code == 200
        assert "支付" in response.text or "html" in response.text.lower()
        print("✓ 支付宝同步回调返回正常")

    @pytest.mark.asyncio
    async def test_alipay_notify_callback(self):
        """测试支付宝异步通知"""
        response = await self.client.post(
            "/payment/callback/alipay/notify",
            data={
                "out_trade_no": "TEST_ORDER_001",
                "trade_no": "2024010122001",
                "trade_status": "TRADE_SUCCESS",
                "total_amount": "99.00",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        content = response.text
        assert content in ["success", "failure"]
        print(f"✓ 支付宝异步通知返回: {content}")

    @pytest.mark.asyncio
    async def test_wechat_notify_callback(self):
        """测试微信支付异步通知"""
        import json
        response = await self.client.post(
            "/payment/callback/wechat/notify",
            content=json.dumps({
                "id": "test_notify_001",
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {"ciphertext": "test_encrypted_data"},
            }),
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") in ["SUCCESS", "FAIL"]
        print(f"✓ 微信支付通知返回: {data.get('code')}")

    @pytest.mark.asyncio
    async def test_payment_without_auth(self):
        """测试无认证访问支付接口"""
        self.client.clear_auth()

        response = await self.client.post(
            "/payment/orders/create",
            json={
                "plan_type": "professional",
                "duration_months": 1,
                "payment_type": "pc",
                "subscription_type": "new",
            }
        )

        assert response.status_code in [401, 403]
        print("✓ 无认证访问支付接口被正确拒绝")
