"""
FastAPI 主应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import (
    admin,
    ai_chat,
    analytics,
    analysis_report,
    audit,
    auth,
    conversation,
    follow_up,
    health,
    intent,
    knowledge,
    monitor,
    order,
    outreach,
    payment,
    platform,
    platform_gateway,
    pdd_webhook,
    product,
    content_generation,
    pricing,
    quality,
    quota,
    rag,
    recommendation,
    segment,
    sensitive_word,
    setup,
    statistics,
    tenant,
    webhook,
    websocket,
)
from core import AppException, settings
from db import close_db, close_redis, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()
    print("✓ 数据库已初始化")

    # 初始化限流中间件
    from db import get_redis
    from api.middleware.rate_limit import RateLimitMiddleware
    redis_client = await get_redis()
    app.state.redis_client = redis_client
    print("✓ 限流中间件已初始化")

    yield

    # 关闭时清理资源
    await close_db()
    await close_redis()
    print("✓ 资源已清理")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="电商智能客服 SaaS 平台 API",
    lifespan=lifespan,
    docs_url=None,  # 禁用默认的 docs，使用自定义的
    redoc_url="/redoc" if settings.debug else None,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 限流中间件 - 需要在lifespan后通过state添加
# 实际添加在 @app.on_event("startup") 中进行

# Prometheus中间件
from utils.prometheus import PrometheusMiddleware, init_app_info
from api.middleware.logging import RequestLoggingMiddleware

app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 初始化应用信息
init_app_info(version=settings.app_version, environment=settings.environment)

# 初始化日志系统
from utils.logger import setup_logging

setup_logging(
    level=settings.log_level, json_format=(settings.log_format == "json"), log_file=None
)

# 初始化Sentry
from utils.sentry import init_sentry

if settings.sentry_dsn:
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1,  # 10%的性能追踪采样率
    )


# 全局异常处理
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义应用异常"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理数据验证异常"""
    errors = exc.errors()
    safe_errors = []
    for err in errors:
        safe_err = {}
        for k, v in err.items():
            if k == "ctx":
                safe_err[k] = {ck: str(cv) for ck, cv in v.items()}
            else:
                safe_err[k] = v
        safe_errors.append(safe_err)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "数据验证失败",
                "details": safe_errors,
            },
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    import traceback

    print(f"未处理的异常: {exc}")
    traceback.print_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
            },
        },
    )


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
    }


# 自定义 Swagger UI 使用国内 CDN
if settings.debug:
    from fastapi.responses import HTMLResponse

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """自定义 Swagger UI 使用国内 CDN"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <link type="text/css" rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <title>{settings.app_name} - Swagger UI</title>
        </head>
        <body>
        <div id="swagger-ui">
        </div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
        const ui = SwaggerUIBundle({{
            url: '/openapi.json',
            dom_id: "#swagger-ui",
            layout: "BaseLayout",
            deepLinking: true,
            showExtensions: true,
            persistAuthorization: true,
        }});
        </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


# 添加限流中间件（需要在路由注册前）
@app.on_event("startup")
async def add_rate_limit_middleware():
    """添加限流中间件"""
    from api.middleware.rate_limit import RateLimitMiddleware
    
    if hasattr(app.state, "redis_client"):
        app.add_middleware(RateLimitMiddleware, redis_client=app.state.redis_client)
        print("✓ 限流中间件已添加")


# 注册路由
from utils.prometheus import router as prometheus_router

app.include_router(prometheus_router)  # Prometheus metrics
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(tenant.router, prefix=settings.api_v1_prefix)
app.include_router(conversation.router, prefix=settings.api_v1_prefix)
app.include_router(knowledge.router, prefix=settings.api_v1_prefix)
app.include_router(payment.router, prefix=settings.api_v1_prefix)
app.include_router(ai_chat.router, prefix=settings.api_v1_prefix)
app.include_router(websocket.router, prefix=settings.api_v1_prefix)
app.include_router(intent.router, prefix=settings.api_v1_prefix)
app.include_router(rag.router, prefix=settings.api_v1_prefix)
app.include_router(monitor.router, prefix=settings.api_v1_prefix)
app.include_router(quality.router, prefix=settings.api_v1_prefix)
app.include_router(webhook.router, prefix=settings.api_v1_prefix)
app.include_router(statistics.router, prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)
app.include_router(sensitive_word.router, prefix=settings.api_v1_prefix)
app.include_router(audit.router, prefix=settings.api_v1_prefix)
app.include_router(setup.router, prefix=settings.api_v1_prefix)
app.include_router(platform.router, prefix=settings.api_v1_prefix)
app.include_router(platform_gateway.router, prefix=settings.api_v1_prefix)
app.include_router(product.router, prefix=settings.api_v1_prefix)
app.include_router(content_generation.router, prefix=settings.api_v1_prefix)
app.include_router(pricing.router, prefix=settings.api_v1_prefix)
app.include_router(order.router, prefix=settings.api_v1_prefix)
app.include_router(analysis_report.router, prefix=settings.api_v1_prefix)
app.include_router(outreach.router, prefix=settings.api_v1_prefix)
app.include_router(segment.router, prefix=settings.api_v1_prefix)
app.include_router(follow_up.router, prefix=settings.api_v1_prefix)
app.include_router(recommendation.router, prefix=settings.api_v1_prefix)
app.include_router(quota.router, prefix=settings.api_v1_prefix)
app.include_router(pdd_webhook.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
