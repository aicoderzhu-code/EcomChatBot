"""
Prometheus指标集成
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from starlette.responses import Response
import time

# ==================== 指标定义 ====================

# 请求指标
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUEST_SIZE = Histogram(
    "http_request_size_bytes",
    "HTTP request size",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
)

HTTP_RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "HTTP response size",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
)

# 业务指标
ACTIVE_CONVERSATIONS = Gauge(
    "active_conversations_total", "Number of active conversations", ["tenant_id"]
)

CONVERSATION_DURATION = Histogram(
    "conversation_duration_seconds",
    "Conversation duration",
    ["tenant_id"],
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)

MESSAGE_COUNT = Counter(
    "messages_total",
    "Total messages",
    ["tenant_id", "direction"],  # direction: inbound/outbound
)

# LLM指标
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status"],  # status: success/error
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total", "Total tokens used", ["model", "type"]  # type: input/output
)

# RAG指标
RAG_RETRIEVAL_DURATION = Histogram(
    "rag_retrieval_duration_seconds",
    "RAG retrieval latency",
    ["tenant_id"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

RAG_RETRIEVAL_RESULTS = Histogram(
    "rag_retrieval_results_count",
    "Number of RAG retrieval results",
    ["tenant_id"],
    buckets=[0, 1, 3, 5, 10, 20],
)

# 系统指标
DB_CONNECTIONS = Gauge("db_connections_total", "Database connections", ["state"])  # state: active/idle

REDIS_CONNECTIONS = Gauge("redis_connections_total", "Redis connections")

CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],  # status: success/failure/retry
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0],
)

# 应用信息
APP_INFO = Info("app", "Application information")


# ==================== 指标收集中间件 ====================


class PrometheusMiddleware:
    """Prometheus指标收集中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # 创建自定义send来捕获状态码
        status_code = 500
        response_size = 0

        async def custom_send(message):
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, custom_send)
        finally:
            # 记录指标
            duration = time.time() - start_time
            method = scope["method"]
            path = scope["path"]

            # 简化路径(移除ID等动态部分)
            endpoint = self._simplify_path(path)

            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status_code).inc()

            HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            HTTP_RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(response_size)

    def _simplify_path(self, path: str) -> str:
        """简化路径,将动态部分替换为占位符"""
        import re

        # UUID模式
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path
        )
        # 数字ID
        path = re.sub(r"/\d+", "/{id}", path)
        return path


# ==================== Metrics端点 ====================

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ==================== 辅助函数 ====================


def record_llm_request(model: str, duration: float, tokens_in: int, tokens_out: int, success: bool):
    """记录LLM请求指标"""
    LLM_REQUESTS_TOTAL.labels(model=model, status="success" if success else "error").inc()
    LLM_REQUEST_DURATION.labels(model=model).observe(duration)
    LLM_TOKENS_TOTAL.labels(model=model, type="input").inc(tokens_in)
    LLM_TOKENS_TOTAL.labels(model=model, type="output").inc(tokens_out)


def record_rag_retrieval(tenant_id: str, duration: float, results_count: int):
    """记录RAG检索指标"""
    RAG_RETRIEVAL_DURATION.labels(tenant_id=tenant_id).observe(duration)
    RAG_RETRIEVAL_RESULTS.labels(tenant_id=tenant_id).observe(results_count)


def update_active_conversations(tenant_id: str, count: int):
    """更新活跃会话数"""
    ACTIVE_CONVERSATIONS.labels(tenant_id=tenant_id).set(count)


def record_message(tenant_id: str, direction: str):
    """记录消息"""
    MESSAGE_COUNT.labels(tenant_id=tenant_id, direction=direction).inc()


def record_conversation_duration(tenant_id: str, duration: float):
    """记录对话时长"""
    CONVERSATION_DURATION.labels(tenant_id=tenant_id).observe(duration)


def init_app_info(version: str, environment: str):
    """初始化应用信息"""
    APP_INFO.info({"version": version, "environment": environment})
