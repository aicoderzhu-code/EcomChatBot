"""
健康检查接口
"""
from datetime import datetime
from typing import Any
import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from db import get_db, get_redis
from core.config import settings


router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check():
    """
    基础健康检查

    用于负载均衡器/K8s探针
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/live")
async def liveness_check():
    """
    存活检查

    K8s livenessProbe使用
    仅检查应用是否存活
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)
):
    """
    就绪检查

    K8s readinessProbe使用
    检查所有依赖服务是否就绪
    """
    checks = {}
    is_ready = True

    # 检查数据库
    try:
        start = datetime.utcnow()
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        checks["database"] = {"status": "healthy", "latency_ms": round(latency, 2)}
    except asyncio.TimeoutError:
        checks["database"] = {"status": "unhealthy", "error": "连接超时"}
        is_ready = False
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 检查Redis
    try:
        start = datetime.utcnow()
        await asyncio.wait_for(redis_client.ping(), timeout=5.0)
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        checks["redis"] = {"status": "healthy", "latency_ms": round(latency, 2)}
    except asyncio.TimeoutError:
        checks["redis"] = {"status": "unhealthy", "error": "连接超时"}
        is_ready = False
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 检查Milvus（可选）
    try:
        from pymilvus import connections

        connections.connect(
            alias="health_check",
            host=settings.milvus_host,
            port=settings.milvus_port,
            timeout=5,
        )
        connections.disconnect("health_check")
        checks["milvus"] = {"status": "healthy"}
    except Exception as e:
        checks["milvus"] = {"status": "unhealthy", "error": str(e)}
        # Milvus不可用不影响就绪状态（可选服务）

    status_code = 200 if is_ready else 503

    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)
):
    """
    详细健康检查

    返回系统详细状态，包括：
    - 系统资源（CPU、内存、磁盘）
    - 数据库连接池状态
    - Redis连接信息
    """
    import psutil
    import platform

    health_info: dict[str, Any] = {}

    # 系统资源
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    health_info["system"] = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
    }

    # 数据库连接池
    try:
        # 获取数据库引擎
        engine = db.get_bind()
        pool = engine.pool

        # 获取连接池状态
        pool_status = {
            "size": pool.size(),
            "checked_in": pool.checkedinconnections(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
        }

        health_info["database"] = {
            "status": "healthy",
            "pool": pool_status,
            "pool_usage_percent": round(
                pool_status["checked_out"] / pool_status["total"] * 100, 2
            )
            if pool_status["total"] > 0
            else 0,
        }
    except Exception as e:
        health_info["database"] = {"status": "error", "error": str(e)}

    # Redis连接
    try:
        redis_info = await redis_client.info()
        health_info["redis"] = {
            "status": "healthy",
            "connected_clients": redis_info.get("connected_clients"),
            "used_memory_human": redis_info.get("used_memory_human"),
            "uptime_days": redis_info.get("uptime_in_days"),
            "total_commands_processed": redis_info.get("total_commands_processed"),
        }
    except Exception as e:
        health_info["redis"] = {"status": "error", "error": str(e)}

    # 应用信息
    health_info["application"] = {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
    }

    health_info["timestamp"] = datetime.utcnow().isoformat()

    return health_info
