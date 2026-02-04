"""
后台任务模块
"""
from tasks.celery_app import celery_app

__all__ = ["celery_app"]
