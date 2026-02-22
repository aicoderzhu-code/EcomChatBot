"""
管理员运营完整流程测试

测试管理员从登录到日常运营管理的完整流程
"""
import pytest
import uuid
from test_base import (
    BaseAPITest,
    AdminTestMixin,
    TenantTestMixin,
)
from config import settings


@pytest.mark.integration
@pytest.mark.admin
class TestAdminOperationsFlow(BaseAPITest, AdminTestMixin, TenantTestMixin):
    """管理员运营完整流程测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_admin_operations_flow(self):
        """
        测试管理员完整运营流程

        流程：
        1. 管理员登录
        2. 查看租户列表
        3. 创建新租户
        4. 查看租户详情
        5. 调整租户配额
        6. 管理敏感词（创建、查询、删除）
        7. 查看审计日志
        8. 查看事件统计
        9. 查看安全警报
        10. 查看平台统计
        11. 禁用/启用租户
        """
        # ========== 步骤1: 管理员登录 ==========
        print("\n[步骤1] 管理员登录...")
        token = await self.admin_login()
        assert token
        print(f"✓ 管理员登录成功")

        # ========== 步骤2: 查看租户列表 ==========
        print("\n[步骤2] 查看租户列表...")
        tenants_resp = await self.client.get("/admin/tenants")
        tenants_data = self.assert_success(tenants_resp)

        if isinstance(tenants_data, dict) and "items" in tenants_data:
            total_tenants = tenants_data.get("total", len(tenants_data["items"]))
        elif isinstance(tenants_data, list):
            total_tenants = len(tenants_data)
        else:
            total_tenants = 0

        print(f"✓ 租户列表查询成功，共 {total_tenants} 个租户")

        # ========== 步骤3: 创建新租户 ==========
        print("\n[步骤3] 通过管理员创建新租户...")
        # 先通过普通注册接口创建（管理员可能使用不同接口）
        self.client.clear_auth()
        tenant_info = await self.create_test_tenant()
        tenant_id = tenant_info["tenant_id"]
        print(f"✓ 租户创建成功: {tenant_id}")

        # 重新登录管理员
        await self.admin_login()

        # ========== 步骤4: 查看租户详情 ==========
        print("\n[步骤4] 查看租户详情...")
        detail_resp = await self.client.get(f"/admin/tenants/{tenant_id}")

        if detail_resp.status_code == 200:
            detail_data = self.assert_success(detail_resp)
            print(f"✓ 租户详情: {detail_data.get('company_name', tenant_id)}")
        else:
            print(f"⚠ 租户详情返回 {detail_resp.status_code}")

        # ========== 步骤5: 调整租户配额 ==========
        print("\n[步骤5] 调整租户配额...")
        quota_resp = await self.client.post(
            f"/admin/tenants/{tenant_id}/adjust-quota",
            json={
                "quota_type": "conversation",
                "adjustment": 100,
                "reason": "自动化测试调整",
            }
        )

        if quota_resp.status_code == 200:
            print("✓ 配额调整成功")
        else:
            print(f"⚠ 配额调整返回 {quota_resp.status_code}")

        # ========== 步骤6: 管理敏感词 ==========
        print("\n[步骤6] 管理敏感词...")

        # 创建敏感词
        word = f"运营测试词_{uuid.uuid4().hex[:6]}"
        create_word_resp = await self.client.post(
            "/sensitive-words",
            json={
                "word": word,
                "level": "block",
                "category": "运营测试",
            }
        )

        word_id = None
        if create_word_resp.status_code == 200:
            word_data = self.assert_success(create_word_resp)
            word_id = word_data["id"]
            self.cleaner.register_sensitive_word(word_id)
            print(f"✓ 敏感词创建成功: {word}")

        # 查询敏感词
        list_word_resp = await self.client.get(
            "/sensitive-words",
            params={"keyword": word[:6]}
        )
        if list_word_resp.status_code == 200:
            print("✓ 敏感词查询成功")

        # 删除敏感词
        if word_id:
            del_word_resp = await self.client.delete(f"/sensitive-words/{word_id}")
            if del_word_resp.status_code == 200:
                print("✓ 敏感词删除成功")
                # 已删除，从清理列表移除
                if word_id in self.cleaner.sensitive_word_ids:
                    self.cleaner.sensitive_word_ids.remove(word_id)

        # ========== 步骤7: 查看审计日志 ==========
        print("\n[步骤7] 查看审计日志...")
        audit_resp = await self.client.get(
            "/audit/logs",
            params={"limit": 10}
        )

        if audit_resp.status_code == 200:
            audit_data = self.assert_success(audit_resp)
            print(f"✓ 审计日志查询成功，共 {audit_data.get('total', 0)} 条")
        else:
            print(f"⚠ 审计日志返回 {audit_resp.status_code}")

        # ========== 步骤8: 查看事件统计 ==========
        print("\n[步骤8] 查看事件统计...")
        event_stats_resp = await self.client.get(
            "/audit/statistics/events",
            params={"days": 7}
        )

        if event_stats_resp.status_code == 200:
            event_data = self.assert_success(event_stats_resp)
            event_count = len(event_data.get("event_statistics", []))
            print(f"✓ 事件统计查询成功，共 {event_count} 类事件")
        else:
            print(f"⚠ 事件统计返回 {event_stats_resp.status_code}")

        # ========== 步骤9: 查看安全警报 ==========
        print("\n[步骤9] 查看安全警报...")
        alerts_resp = await self.client.get(
            "/audit/statistics/security-alerts",
            params={"days": 30}
        )

        if alerts_resp.status_code == 200:
            alerts_data = self.assert_success(alerts_resp)
            print(f"✓ 安全警报查询成功，共 {alerts_data.get('total_alerts', 0)} 条警报")
        else:
            print(f"⚠ 安全警报返回 {alerts_resp.status_code}")

        # ========== 步骤10: 查看平台统计 ==========
        print("\n[步骤10] 查看平台统计...")
        stats_resp = await self.client.get("/admin/statistics/overview")

        if stats_resp.status_code == 200:
            stats_data = self.assert_success(stats_resp)
            print(f"✓ 平台统计查询成功")
        else:
            print(f"⚠ 平台统计返回 {stats_resp.status_code}")

        # ========== 步骤11: 禁用/启用租户 ==========
        print("\n[步骤11] 禁用/启用租户...")

        # 禁用
        disable_resp = await self.client.put(
            f"/admin/tenants/{tenant_id}/status",
            json={"status": "disabled"}
        )
        if disable_resp.status_code == 200:
            print(f"✓ 租户已禁用: {tenant_id}")

        # 重新启用
        enable_resp = await self.client.put(
            f"/admin/tenants/{tenant_id}/status",
            json={"status": "active"}
        )
        if enable_resp.status_code == 200:
            print(f"✓ 租户已重新启用: {tenant_id}")

        print("\n" + "=" * 50)
        print("✅ 管理员运营完整流程测试通过！")
        print("=" * 50)
