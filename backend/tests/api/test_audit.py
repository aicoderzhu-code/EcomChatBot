"""
审计日志 API 测试

覆盖审计日志查询、筛选、统计、安全警报等管理员接口
注意：当前后端未部署审计日志模块（/api/v1/audit/* 路由不存在），全部跳过
"""
import pytest
from test_base import BaseAPITest, AdminTestMixin, TenantTestMixin
from config import settings


@pytest.mark.audit
@pytest.mark.admin
@pytest.mark.skip(reason="审计日志 API 尚未部署，/api/v1/audit/* 路由不存在")
class TestAudit(BaseAPITest, AdminTestMixin, TenantTestMixin):
    """审计日志 API 测试"""

    @pytest.mark.asyncio
    async def test_get_audit_logs(self):
        """测试查询审计日志"""
        await self.admin_login()

        response = await self.client.get(
            "/audit/logs",
            params={"limit": 20, "offset": 0}
        )

        data = self.assert_success(response)
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
        print(f"✓ 审计日志查询成功，共 {data['total']} 条")

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self):
        """测试按条件筛选审计日志"""
        await self.admin_login()

        # 按事件类型筛选
        response = await self.client.get(
            "/audit/logs",
            params={
                "event_type": "tenant.login",
                "limit": 10,
            }
        )

        data = self.assert_success(response)
        assert "logs" in data
        print(f"✓ 按事件类型筛选成功，匹配 {len(data['logs'])} 条")

    @pytest.mark.asyncio
    async def test_get_audit_logs_by_severity(self):
        """测试按严重程度筛选"""
        await self.admin_login()

        response = await self.client.get(
            "/audit/logs",
            params={
                "severity": "INFO",
                "limit": 10,
            }
        )

        data = self.assert_success(response)
        assert "logs" in data
        print(f"✓ 按严重程度筛选成功，匹配 {len(data['logs'])} 条")

    @pytest.mark.asyncio
    async def test_get_audit_logs_pagination(self):
        """测试审计日志分页"""
        await self.admin_login()

        # 第一页
        resp1 = await self.client.get(
            "/audit/logs",
            params={"limit": 5, "offset": 0}
        )
        data1 = self.assert_success(resp1)

        # 第二页
        resp2 = await self.client.get(
            "/audit/logs",
            params={"limit": 5, "offset": 5}
        )
        data2 = self.assert_success(resp2)

        assert data1["offset"] == 0
        assert data2["offset"] == 5
        print("✓ 审计日志分页正常")

    @pytest.mark.asyncio
    async def test_get_audit_log_detail(self):
        """测试获取审计日志详情"""
        await self.admin_login()

        # 先获取列表，取第一条的 ID
        list_resp = await self.client.get(
            "/audit/logs",
            params={"limit": 1}
        )
        list_data = self.assert_success(list_resp)

        if list_data["logs"]:
            log_id = list_data["logs"][0]["id"]
            response = await self.client.get(f"/audit/logs/{log_id}")
            data = self.assert_success(response)
            assert data["id"] == log_id
            print(f"✓ 审计日志详情查询成功: {log_id}")
        else:
            print("⚠ 暂无审计日志数据")

    @pytest.mark.asyncio
    async def test_get_event_statistics(self):
        """测试审计事件统计"""
        await self.admin_login()

        response = await self.client.get(
            "/audit/statistics/events",
            params={"days": 7}
        )

        data = self.assert_success(response)
        assert "event_statistics" in data
        assert "severity_statistics" in data
        assert "daily_statistics" in data
        assert data["period_days"] == 7
        print("✓ 审计事件统计查询成功")

    @pytest.mark.asyncio
    async def test_get_security_alerts(self):
        """测试安全警报查询"""
        await self.admin_login()

        response = await self.client.get(
            "/audit/statistics/security-alerts",
            params={"days": 30, "limit": 20}
        )

        data = self.assert_success(response)
        assert "alerts" in data
        assert "event_counts" in data
        assert "total_alerts" in data
        print(f"✓ 安全警报查询成功，共 {data['total_alerts']} 条")

    @pytest.mark.asyncio
    async def test_get_top_ips(self):
        """测试活跃 IP 统计"""
        await self.admin_login()

        response = await self.client.get(
            "/audit/statistics/top-ips",
            params={"days": 7, "limit": 10}
        )

        data = self.assert_success(response)
        assert "top_ips" in data
        assert isinstance(data["top_ips"], list)
        print(f"✓ 活跃 IP 统计成功，共 {len(data['top_ips'])} 个 IP")

    @pytest.mark.asyncio
    async def test_audit_logs_date_range(self):
        """测试日期范围筛选"""
        await self.admin_login()

        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        response = await self.client.get(
            "/audit/logs",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": 20,
            }
        )

        data = self.assert_success(response)
        assert "logs" in data
        print(f"✓ 日期范围筛选成功，匹配 {len(data['logs'])} 条")

    @pytest.mark.asyncio
    async def test_audit_logs_without_admin(self):
        """测试非管理员访问审计日志"""
        # 使用普通租户凭证
        tenant_info = await self.create_test_tenant()
        self.client.clear_auth()
        self.client.set_api_key(tenant_info["api_key"])

        response = await self.client.get("/audit/logs")
        assert response.status_code in [401, 403]
        print("✓ 非管理员访问审计日志被正确拒绝")

    @pytest.mark.asyncio
    async def test_audit_event_statistics_by_tenant(self):
        """测试按租户筛选事件统计"""
        await self.admin_login()

        # 先创建租户产生一些事件
        tenant_info = await self.create_test_tenant()

        # 重新登录管理员
        await self.admin_login()

        response = await self.client.get(
            "/audit/statistics/events",
            params={
                "tenant_id": tenant_info["tenant_id"],
                "days": 7,
            }
        )

        data = self.assert_success(response)
        assert "event_statistics" in data
        print(f"✓ 按租户筛选事件统计成功")
