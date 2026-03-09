"""
Celery 应用实例
"""
import logging
from celery import Celery
from celery.schedules import crontab
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
        "tasks.webhook_tasks",
        "tasks.platform_tasks",
        "tasks.product_sync_tasks",
        "tasks.generation_tasks",
        "tasks.outreach_tasks",
        "tasks.conversation_tasks",
        "tasks.knowledge_tasks",
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
        "tasks.webhook_tasks.*": {"queue": "webhooks"},
        "tasks.platform_tasks.*": {"queue": "default"},
        "tasks.product_sync_tasks.*": {"queue": "data_processing"},
        "tasks.generation_tasks.*": {"queue": "data_processing"},
        "tasks.outreach_tasks.*": {"queue": "notifications"},
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
    # 每天凌晨1点检查即将过期的订阅
    "check-expiring-subscriptions": {
        "task": "tasks.billing_tasks.check_expiring_subscriptions",
        "schedule": 3600.0 * 24,  # 每天执行一次
    },
    # 每月1号凌晨3点生成月度账单
    "generate-monthly-bills": {
        "task": "tasks.billing_tasks.generate_monthly_bills",
        "schedule": crontab(hour=3, day_of_month=1),  # 每月1号3点
    },
    # 每月1号凌晨0点重置配额
    "reset-monthly-quotas": {
        "task": "tasks.billing_tasks.reset_monthly_quotas",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),
        "options": {"queue": "billing"},
    },
    # 每5分钟重试失败的 Webhook
    "retry-failed-webhooks": {
        "task": "tasks.webhook_tasks.retry_failed_webhooks",
        "schedule": 300.0,  # 每5分钟执行一次
    },
    # 每天清理30天前的 Webhook 日志
    "cleanup-old-webhook-logs": {
        "task": "tasks.webhook_tasks.cleanup_old_webhook_logs",
        "schedule": 3600.0 * 24,  # 每24小时执行一次
        "args": (30,),  # 保留30天
    },
    # 每天凌晨4点检查服务降级
    "check-service-degradation": {
        "task": "tasks.billing_tasks.check_service_degradation",
        "schedule": crontab(hour=4, minute=0),  # 每天凌晨4点
        "options": {"queue": "billing"}
    },
    # 每天凌晨2点处理订阅续费
    "process-subscription-renewal": {
        "task": "tasks.billing_tasks.process_subscription_renewal",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
        "options": {"queue": "billing"}
    },
    # 每5分钟检查需要执行的商品同步调度
    "run-scheduled-product-syncs": {
        "task": "tasks.product_sync_tasks.run_scheduled_syncs",
        "schedule": 300.0,  # 每5分钟检查一次
    },
    # 每30分钟检查并刷新即将过期的平台 access_token
    "refresh-platform-tokens": {
        "task": "tasks.platform_tasks.refresh_expiring_tokens",
        "schedule": 1800.0,
    },
    # 每10分钟评估自动触发规则
    "evaluate-outreach-rules": {
        "task": "tasks.outreach_tasks.evaluate_auto_rules",
        "schedule": 600.0,
        "options": {"queue": "notifications"},
    },
    # 每5分钟处理到期跟进计划
    "process-follow-ups": {
        "task": "tasks.outreach_tasks.process_follow_ups",
        "schedule": 300.0,
        "options": {"queue": "notifications"},
    },
    # 每小时刷新动态分群
    "refresh-dynamic-segments": {
        "task": "tasks.outreach_tasks.refresh_dynamic_segments",
        "schedule": 3600.0,
        "options": {"queue": "notifications"},
    },
}

logger.info("Celery 应用初始化完成")
