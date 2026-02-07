"""
结构化日志工具
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON日志格式化器"""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # 添加日志级别
        log_record["level"] = record.levelname

        # 添加来源信息
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # 添加进程/线程信息
        log_record["process_id"] = record.process
        log_record["thread_id"] = record.thread

        # 移除默认字段
        log_record.pop("levelname", None)
        log_record.pop("name", None)


def setup_logging(level: str = "INFO", json_format: bool = True, log_file: str = None):
    """配置日志系统"""

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    if json_format:
        formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(logger)s %(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class RequestLogger:
    """请求日志记录器"""

    def __init__(self, logger_name: str = "request"):
        self.logger = logging.getLogger(logger_name)

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        tenant_id: str = None,
        user_id: str = None,
        ip: str = None,
        user_agent: str = None,
        extra: dict = None,
    ):
        """记录请求开始"""
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "ip": ip,
                "user_agent": user_agent,
                **(extra or {}),
            },
        )

    def log_response(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        response_size: int = None,
        extra: dict = None,
    ):
        """记录请求结束"""
        level = (
            logging.INFO
            if status_code < 400
            else logging.WARNING
            if status_code < 500
            else logging.ERROR
        )

        self.logger.log(
            level,
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "response_size": response_size,
                **(extra or {}),
            },
        )

    def log_error(self, request_id: str, error: Exception, extra: dict = None):
        """记录错误"""
        self.logger.error(
            "Request error",
            extra={
                "request_id": request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **(extra or {}),
            },
            exc_info=True,
        )


# 全局实例
request_logger = RequestLogger()
