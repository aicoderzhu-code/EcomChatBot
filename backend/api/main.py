"""
FastAPI 主应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import admin, ai_chat, auth, conversation, intent, knowledge, payment, rag, tenant, websocket, monitor, quality, webhook, model_config
from core import AppException, settings
from db import close_db, close_redis, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()
    print("✓ 数据库已初始化")

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
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "数据验证失败",
                "details": exc.errors(),
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


# 注册路由
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
app.include_router(model_config.router, prefix=settings.api_v1_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
