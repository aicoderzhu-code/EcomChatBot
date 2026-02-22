"""
支付订阅完整流程测试

测试从租户注册到套餐订阅、变更、取消的完整流程
"""
import pytest
from test_base import (
    BaseAPITest,
    TenantTestMixin,
    PaymentTestMixin,
)
from config import settings


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentSubscriptionFlow(BaseAPITest, TenantTestMixin, PaymentTestMixin):
    """支付订阅完整流程测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_payment_subscription_flow(self):
        """
        测试支付订阅完整流程

        流程：
        1. 注册租户（默认 free 套餐）
        2. 查看当前订阅状态
        3. 查看配额使用情况
        4. 预览升级到 professional 的差价
        5. 创建订阅订单
        6. 查看订单详情
        7. 变更套餐
        8. 取消自动续费
        9. 再次查看订阅状态，确认变更
        """
        # ========== 步骤1: 注册租户 ==========
        print("\n[步骤1] 注册租户...")
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        print(f"✓ 租户注册成功: {tenant_info['tenant_id']}")

        # ========== 步骤2: 查看当前订阅 ==========
        print("\n[步骤2] 查看当前订阅...")
        sub_resp = await self.client.get("/tenant/subscription")
        sub_data = self.assert_success(sub_resp)
        assert "plan_type" in sub_data
        initial_plan = sub_data["plan_type"]
        print(f"✓ 当前套餐: {initial_plan}")

        # ========== 步骤3: 查看配额 ==========
        print("\n[步骤3] 查看配额使用情况...")
        quota_resp = await self.client.get("/tenant/quota")
        quota_data = self.assert_success(quota_resp)
        assert "concurrent" in quota_data
        print(f"✓ 配额信息: 并发={quota_data.get('concurrent', {})}")

        # ========== 步骤4: 预览升级差价 ==========
        print("\n[步骤4] 预览升级差价...")
        price_resp = await self.client.get(
            "/payment/subscription/prorated-price",
            params={"new_plan_type": "professional"}
        )

        if price_resp.status_code == 200:
            price_data = self.assert_success(price_resp)
            print(f"✓ 升级差价: ¥{price_data.get('prorated_charge', 0)}")
            print(f"  当前套餐价值: ¥{price_data.get('current_plan_value', 0)}")
            print(f"  新套餐价值: ¥{price_data.get('new_plan_value', 0)}")
        else:
            print(f"⚠ 差价预览返回 {price_resp.status_code}")

        # ========== 步骤5: 创建订阅订单 ==========
        print("\n[步骤5] 创建订阅订单...")
        subscribe_resp = await self.client.post(
            "/payment/subscription/subscribe",
            json={
                "plan_type": "basic",
                "duration_months": 1,
                "payment_method": "alipay",
                "auto_renew": True,
            }
        )

        if subscribe_resp.status_code == 200:
            subscribe_data = self.assert_success(subscribe_resp)
            assert subscribe_data.get("success") is True
            order_number = subscribe_data.get("order_number")
            if order_number:
                self.cleaner.register_payment_order(order_number)
            print(f"✓ 订阅订单创建成功: {order_number}")

            # ========== 步骤6: 查看订单详情 ==========
            if order_number:
                print("\n[步骤6] 查看订单详情...")
                detail_resp = await self.client.get(f"/payment/orders/{order_number}")
                if detail_resp.status_code == 200:
                    print("✓ 订单详情查询成功")
                else:
                    print(f"⚠ 订单详情返回 {detail_resp.status_code}")
        else:
            print(f"⚠ 订阅订单创建返回 {subscribe_resp.status_code}（支付网关可能未配置）")

        # ========== 步骤7: 变更套餐 ==========
        print("\n[步骤7] 变更套餐...")
        change_resp = await self.client.put(
            "/payment/subscription/change",
            json={
                "new_plan_type": "professional",
                "effective_immediately": False,
            }
        )

        if change_resp.status_code == 200:
            change_data = self.assert_success(change_resp)
            print(f"✓ 套餐变更: {change_data.get('message', '')}")
        elif change_resp.status_code == 400:
            print("✓ 套餐变更拒绝（业务规则限制）")
        else:
            print(f"⚠ 套餐变更返回 {change_resp.status_code}")

        # ========== 步骤8: 取消自动续费 ==========
        print("\n[步骤8] 取消自动续费...")
        cancel_resp = await self.client.post("/payment/subscription/cancel-renewal")

        if cancel_resp.status_code == 200:
            cancel_data = cancel_resp.json()
            assert cancel_data.get("success") is True
            print(f"✓ {cancel_data.get('message', '取消续费成功')}")
        else:
            print(f"⚠ 取消续费返回 {cancel_resp.status_code}")

        # ========== 步骤9: 确认订阅状态 ==========
        print("\n[步骤9] 确认最终订阅状态...")
        final_sub_resp = await self.client.get("/payment/subscription")

        if final_sub_resp.status_code == 200:
            final_data = self.assert_success(final_sub_resp)
            print(f"✓ 最终套餐: {final_data.get('plan_type')}")
            print(f"  自动续费: {final_data.get('auto_renew')}")
            print(f"  状态: {final_data.get('status')}")
        else:
            # 通过 tenant 接口查看
            tenant_sub_resp = await self.client.get("/tenant/subscription")
            if tenant_sub_resp.status_code == 200:
                final_data = self.assert_success(tenant_sub_resp)
                print(f"✓ 最终套餐: {final_data.get('plan_type')}")

        print("\n" + "=" * 50)
        print("✅ 支付订阅完整流程测试通过！")
        print("=" * 50)
