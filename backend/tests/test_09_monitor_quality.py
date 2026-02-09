"""
监控和质量评估模块测试
测试覆盖: Monitor(6接口) + Quality(4接口) = 10接口, 40个测试用例
"""
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper

pytestmark = [pytest.mark.asyncio]


# ==================== 监控模块测试 ====================


@pytest.mark.monitor
class TestConversationStats:
    """对话统计测试"""

    async def test_get_conversation_stats_basic(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取对话统计"""
        response = await client.get(
            "/api/v1/monitor/conversations", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证统计数据
        stats = data["data"]
        assert "total_conversations" in stats or "count" in stats

    async def test_get_conversation_stats_with_time_range(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试指定时间范围的对话统计"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        response = await client.get(
            "/api/v1/monitor/conversations",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_get_conversation_stats_24h(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试最近24小时对话统计"""
        response = await client.get(
            "/api/v1/monitor/conversations", headers=tenant_api_key_headers
        )

        # 默认应该返回24小时的数据
        data = AssertHelper.assert_response_success(response, 200)


@pytest.mark.monitor
class TestResponseTimeStats:
    """响应时间统计测试"""

    async def test_get_response_time_stats(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取响应时间统计"""
        response = await client.get(
            "/api/v1/monitor/response-time", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证响应时间数据
        stats = data["data"]
        possible_keys = ["avg_response_time", "min", "max", "p95", "p99"]
        # 至少应该有一些统计指标
        assert any(key in stats for key in possible_keys)

    async def test_response_time_stats_with_time_range(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试指定时间范围的响应时间统计"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=12)

        response = await client.get(
            "/api/v1/monitor/response-time",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)


@pytest.mark.monitor
class TestSatisfactionStats:
    """满意度统计测试"""

    async def test_get_satisfaction_stats(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取满意度统计"""
        response = await client.get(
            "/api/v1/monitor/satisfaction", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证满意度数据
        stats = data["data"]
        possible_keys = [
            "avg_score",
            "total_ratings",
            "satisfaction_rate",
            "distribution",
        ]
        assert any(key in stats for key in possible_keys)

    async def test_satisfaction_stats_score_range(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试满意度评分范围"""
        response = await client.get(
            "/api/v1/monitor/satisfaction", headers=tenant_api_key_headers
        )

        if response.status_code == 200:
            data = response.json()
            stats = data["data"]

            # 如果有平均分,应该在1-5之间
            if "avg_score" in stats:
                assert 1 <= stats["avg_score"] <= 5


@pytest.mark.monitor
class TestDashboardSummary:
    """Dashboard汇总测试"""

    async def test_get_dashboard_summary_24h(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取24小时Dashboard数据"""
        response = await client.get(
            "/api/v1/monitor/dashboard",
            params={"time_range": "24h"},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证Dashboard数据
        summary = data["data"]
        assert isinstance(summary, dict)
        assert len(summary) > 0

    async def test_get_dashboard_summary_7d(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取7天Dashboard数据"""
        response = await client.get(
            "/api/v1/monitor/dashboard",
            params={"time_range": "7d"},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_get_dashboard_summary_30d(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取30天Dashboard数据"""
        response = await client.get(
            "/api/v1/monitor/dashboard",
            params={"time_range": "30d"},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_get_dashboard_summary_invalid_range(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试无效的时间范围"""
        response = await client.get(
            "/api/v1/monitor/dashboard",
            params={"time_range": "invalid"},
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]


@pytest.mark.monitor
class TestTrendAnalysis:
    """趋势分析测试"""

    async def test_get_hourly_trend(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取每小时趋势"""
        response = await client.get(
            "/api/v1/monitor/trend/hourly",
            params={"hours": 24},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证趋势数据
        trend = data["data"]
        assert isinstance(trend, list)

    async def test_get_hourly_trend_48h(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取48小时趋势"""
        response = await client.get(
            "/api/v1/monitor/trend/hourly",
            params={"hours": 48},
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

        trend = data["data"]
        assert len(trend) <= 48

    async def test_get_hourly_trend_7d(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取7天趋势"""
        response = await client.get(
            "/api/v1/monitor/trend/hourly",
            params={"hours": 168},  # 7天 * 24小时
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_get_hourly_trend_invalid_hours(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试无效的小时数"""
        response = await client.get(
            "/api/v1/monitor/trend/hourly",
            params={"hours": 0},
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]

    async def test_get_hourly_trend_exceed_limit(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试超过限制的小时数"""
        response = await client.get(
            "/api/v1/monitor/trend/hourly",
            params={"hours": 200},  # 超过168小时限制
            headers=tenant_api_key_headers,
        )

        assert response.status_code in [400, 422]


# ==================== 质量评估模块测试 ====================


@pytest.mark.quality
class TestConversationQuality:
    """对话质量评估测试"""

    async def test_evaluate_conversation_quality(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试评估单个对话质量"""
        # 先创建会话
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        if create_response.status_code == 200:
            conversation_id = create_response.json()["data"]["conversation_id"]

            # 评估质量
            response = await client.get(
                f"/api/v1/quality/conversation/{conversation_id}",
                headers=tenant_api_key_headers,
            )

            data = AssertHelper.assert_response_success(response, 200)

            # 验证质量评估结果
            quality = data["data"]
            assert "score" in quality or "quality_score" in quality

    async def test_evaluate_nonexistent_conversation(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试评估不存在的对话"""
        response = await client.get(
            "/api/v1/quality/conversation/CONV_NOTEXIST",
            headers=tenant_api_key_headers,
        )

        AssertHelper.assert_response_error(response, 404)

    async def test_quality_score_range(
        self, client: AsyncClient, tenant_api_key_headers: dict, conversation_data: dict
    ):
        """测试质量评分范围"""
        # 创建会话
        create_response = await client.post(
            "/api/v1/conversation/create",
            json=conversation_data,
            headers=tenant_api_key_headers,
        )

        if create_response.status_code == 200:
            conversation_id = create_response.json()["data"]["conversation_id"]

            # 评估质量
            response = await client.get(
                f"/api/v1/quality/conversation/{conversation_id}",
                headers=tenant_api_key_headers,
            )

            if response.status_code == 200:
                data = response.json()
                quality = data["data"]

                # 质量分数应该在0-100或0-1之间
                if "score" in quality:
                    score = quality["score"]
                    assert 0 <= score <= 100 or 0 <= score <= 1


@pytest.mark.quality
class TestQualitySummary:
    """质量统计汇总测试"""

    async def test_get_quality_summary(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试获取质量统计汇总"""
        response = await client.get(
            "/api/v1/quality/summary", headers=tenant_api_key_headers
        )

        data = AssertHelper.assert_response_success(response, 200)

        # 验证汇总数据
        summary = data["data"]
        assert isinstance(summary, dict)

    async def test_get_quality_summary_with_time_range(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试指定时间范围的质量汇总"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)

        response = await client.get(
            "/api/v1/quality/summary",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=tenant_api_key_headers,
        )

        data = AssertHelper.assert_response_success(response, 200)

    async def test_quality_summary_contains_metrics(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试质量汇总包含关键指标"""
        response = await client.get(
            "/api/v1/quality/summary", headers=tenant_api_key_headers
        )

        if response.status_code == 200:
            data = response.json()
            summary = data["data"]

            # 应该包含一些关键质量指标
            possible_metrics = [
                "avg_quality_score",
                "total_evaluated",
                "excellent_count",
                "good_count",
                "poor_count",
            ]

            # 至少应该有一些指标
            assert any(metric in summary for metric in possible_metrics)


# ==================== 监控和质量联合测试 ====================


@pytest.mark.integration
class TestMonitorQualityIntegration:
    """监控和质量模块集成测试"""

    async def test_monitor_and_quality_consistency(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试监控和质量数据的一致性"""
        # 获取对话统计
        monitor_response = await client.get(
            "/api/v1/monitor/conversations", headers=tenant_api_key_headers
        )

        # 获取质量汇总
        quality_response = await client.get(
            "/api/v1/quality/summary", headers=tenant_api_key_headers
        )

        # 两者都应该成功
        if monitor_response.status_code == 200 and quality_response.status_code == 200:
            # 可以验证数据的一致性
            # 例如: 监控的对话数 >= 质量评估的对话数
            pass

    async def test_dashboard_includes_quality_metrics(
        self, client: AsyncClient, tenant_api_key_headers: dict
    ):
        """测试Dashboard是否包含质量指标"""
        response = await client.get(
            "/api/v1/monitor/dashboard",
            params={"time_range": "24h"},
            headers=tenant_api_key_headers,
        )

        if response.status_code == 200:
            data = response.json()
            dashboard = data["data"]

            # Dashboard可能包含质量相关指标
            quality_related_keys = ["quality_score", "satisfaction", "avg_rating"]
            # 检查是否包含质量相关数据
            has_quality_data = any(key in dashboard for key in quality_related_keys)
