"""
Celery 应用实例
"""
import logging
from celery import Celery
from core.config import settings

logger = logging.getLogger(__name__)

# 创建 Celery 应用实例
celery_app = Celery(
    "ecom_chatbot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.notification_tasks",
        "tasks.data_tasks",
        "tasks.billing_tasks",
    ],
)

# Celery 配置
celery_app.conf.update(
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 结果过期时间（秒）
    result_expires=3600,

    # 任务超时时间
    task_time_limit=600,  # 硬限制 10分钟
    task_soft_time_limit=540,  # 软限制 9分钟

    # 任务结果后端配置
    result_backend_transport_options={
        "master_name": "mymaster",
    },

    # Worker 配置
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # 任务路由
    task_routes={
        "tasks.notification_tasks.*": {"queue": "notifications"},
        "tasks.data_tasks.*": {"queue": "data_processing"},
        "tasks.billing_tasks.*": {"queue": "billing"},
    },

    # 默认队列
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

# 定期任务配置（使用 Celery Beat）
celery_app.conf.beat_schedule = {
    # 每天凌晨2点清理过期数据
    "cleanup-expired-data": {
        "task": "tasks.data_tasks.cleanup_expired_data",
        "schedule": 3600.0 * 24,  # 每24小时执行一次
    },
    # 每小时同步订单状态
    "sync-order-status": {
        "task": "tasks.billing_tasks.sync_pending_orders",
        "schedule": 3600.0,  # 每小时执行一次
    },
}

logger.info("Celery 应用初始化完成")
