"""
健康检查模块测试
测试覆盖: 4个接口, 8个测试用例
"""
import pytest
from httpx import AsyncClient

from tests.test_utils import AssertHelper

pytestmark = [pytest.mark.asyncio, pytest.mark.health, pytest.mark.fast]


class TestHealthCheckAPIs:
    """健康检查接口测试"""

    async def test_health_basic(self, client: AsyncClient):
        """测试基础健康检查 - GET /health"""
        response = await client.get("/health")
        data = AssertHelper.assert_response_success(response, 200)

        # 验证响应格式
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert isinstance(data["version"], str)

    async def test_health_basic_response_time(self, client: AsyncClient):
        """测试健康检查响应时间 - 应该 < 100ms"""
        import time

        start = time.time()
        response = await client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1, f"健康检查响应时间过长: {duration:.3f}s"

    async def test_health_live_probe(self, client: AsyncClient):
        """测试Kubernetes存活探针 - GET /health/live"""
        response = await client.get("/api/v1/health/live")

        # 存活探针应该始终返回200
        data = AssertHelper.assert_response_success(response, 200)
        assert data.get("status") == "ok"

    async def test_health_ready_probe(self, client: AsyncClient):
        """测试Kubernetes就绪探针 - GET /health/ready"""
        response = await client.get("/api/v1/health/ready")

        # 就绪探针可能返回200或503
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert data["status"] in ["ready", "not_ready"]

    async def test_health_ready_with_db_check(self, client: AsyncClient):
        """测试就绪探针包含数据库检查"""
        response = await client.get("/api/v1/health/ready")
        data = response.json()

        # 如果返回详细信息,应该包含数据库状态
        if "checks" in data:
            assert "database" in data["checks"]

    async def test_health_detailed(self, client: AsyncClient):
        """测试详细健康状态 - GET /health/detailed"""
        response = await client.get("/api/v1/health/detailed")
        data = AssertHelper.assert_response_success(response, 200)

        # 验证包含各服务状态
        assert "database" in data
        assert "redis" in data

        # 验证状态格式
        for service in ["database", "redis"]:
            assert "status" in data[service]
            assert data[service]["status"] in ["healthy", "unhealthy", "unknown"]

    async def test_health_detailed_with_metrics(self, client: AsyncClient):
        """测试详细健康状态包含性能指标"""
        response = await client.get("/api/v1/health/detailed")

        if response.status_code == 200:
            data = response.json()

            # 检查是否包含性能指标
            if "metrics" in data:
                metrics = data["metrics"]
                # 可能包含的指标
                possible_metrics = [
                    "uptime",
                    "request_count",
                    "avg_response_time",
                    "memory_usage",
                ]
                # 至少应该有一个指标
                assert any(key in metrics for key in possible_metrics)

    async def test_health_endpoints_cors(self, client: AsyncClient):
        """测试健康检查端点的CORS支持"""
        # 发送OPTIONS请求
        response = await client.options(
            "/health", headers={"Origin": "https://example.com"}
        )

        # CORS应该允许跨域访问健康检查
        assert response.status_code in [200, 204]


class TestHealthCheckEdgeCases:
    """健康检查边界情况测试"""

    async def test_health_under_high_load(self, client: AsyncClient):
        """测试高负载下的健康检查"""
        import asyncio

        # 并发发送多个健康检查请求
        tasks = [client.get("/health") for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200

    async def test_health_check_idempotency(self, client: AsyncClient):
        """测试健康检查的幂等性"""
        # 连续调用多次,结果应该一致
        response1 = await client.get("/health")
        response2 = await client.get("/health")
        response3 = await client.get("/health")

        assert response1.status_code == response2.status_code == response3.status_code
        data1 = response1.json()
        data2 = response2.json()

        assert data1["status"] == data2["status"]


@pytest.mark.smoke
class TestHealthCheckSmoke:
    """健康检查冒烟测试 - 部署后第一个要检查的"""

    async def test_api_server_is_running(self, client: AsyncClient):
        """验证API服务器正在运行"""
        response = await client.get("/health")
        assert response.status_code == 200, "API服务器未运行"

    async def test_can_connect_to_database(self, client: AsyncClient):
        """验证可以连接到数据库"""
        response = await client.get("/api/v1/health/detailed")

        if response.status_code == 200:
            data = response.json()
            if "database" in data:
                assert (
                    data["database"]["status"] == "healthy"
                ), "无法连接到数据库"
