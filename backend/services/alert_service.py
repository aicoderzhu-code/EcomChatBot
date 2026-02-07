"""
告警服务 - 规则引擎和通知
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import httpx
import logging

from core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """告警渠道"""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"
    SLACK = "slack"


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    description: str
    metric: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5  # 冷却时间,避免重复告警
    enabled: bool = True


@dataclass
class Alert:
    """告警实例"""

    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    tenant_id: Optional[str]
    triggered_at: datetime


class AlertService:
    """告警服务"""

    # 预定义规则
    DEFAULT_RULES = [
        AlertRule(
            name="high_response_time",
            description="响应时间过高",
            metric="response_time_p95",
            condition="gt",
            threshold=3000,  # 3秒
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.DINGTALK, AlertChannel.EMAIL],
        ),
        AlertRule(
            name="critical_response_time",
            description="响应时间严重过高",
            metric="response_time_p99",
            condition="gt",
            threshold=5000,  # 5秒
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SMS, AlertChannel.DINGTALK],
        ),
        AlertRule(
            name="low_resolution_rate",
            description="解决率过低",
            metric="resolution_rate",
            condition="lt",
            threshold=70,  # 70%
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL],
        ),
        AlertRule(
            name="high_error_rate",
            description="错误率过高",
            metric="error_rate",
            condition="gt",
            threshold=5,  # 5%
            severity=AlertSeverity.ERROR,
            channels=[AlertChannel.DINGTALK, AlertChannel.SMS],
        ),
        AlertRule(
            name="quota_warning",
            description="配额使用率告警",
            metric="quota_usage_percentage",
            condition="gt",
            threshold=80,  # 80%
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL],
        ),
        AlertRule(
            name="quota_critical",
            description="配额即将耗尽",
            metric="quota_usage_percentage",
            condition="gt",
            threshold=95,  # 95%
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SMS, AlertChannel.EMAIL],
        ),
    ]

    def __init__(self, metrics_service, notification_service, redis):
        self.metrics_service = metrics_service
        self.notification_service = notification_service
        self.redis = redis
        self.rules = {r.name: r for r in self.DEFAULT_RULES}

    async def check_alerts(self, tenant_id: Optional[str] = None):
        """检查所有告警规则"""
        metrics = await self._collect_metrics(tenant_id)

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            metric_value = metrics.get(rule.metric)
            if metric_value is None:
                continue

            if self._check_condition(metric_value, rule.condition, rule.threshold):
                # 检查冷却期
                if await self._is_in_cooldown(rule_name, tenant_id):
                    continue

                # 触发告警
                alert = Alert(
                    rule_name=rule_name,
                    severity=rule.severity,
                    message=f"{rule.description}: {rule.metric}={metric_value} (阈值: {rule.threshold})",
                    metric_value=metric_value,
                    threshold=rule.threshold,
                    tenant_id=tenant_id,
                    triggered_at=datetime.utcnow(),
                )

                await self._send_alert(alert, rule.channels)
                await self._set_cooldown(rule_name, tenant_id, rule.cooldown_minutes)

    async def _collect_metrics(self, tenant_id: Optional[str] = None) -> dict:
        """收集当前指标"""
        metrics = {}

        # 响应时间
        response_stats = await self.metrics_service.get_response_time_stats(tenant_id)
        metrics["response_time_p50"] = response_stats["p50"]
        metrics["response_time_p95"] = response_stats["p95"]
        metrics["response_time_p99"] = response_stats["p99"]
        metrics["response_time_avg"] = response_stats["avg"]

        # 对话统计
        if tenant_id:
            conv_stats = await self.metrics_service.get_conversation_stats(tenant_id)
            metrics["resolution_rate"] = conv_stats["resolution_rate"]
            metrics["transfer_rate"] = conv_stats["transfer_rate"]

            # 配额使用率（需要从QuotaService获取）
            try:
                quota_status = await self._get_quota_usage(tenant_id)
                metrics["quota_usage_percentage"] = (
                    quota_status.get("conversation", {}).get("percentage", 0)
                )
            except Exception as e:
                logger.error(f"获取配额使用率失败: {e}")
                metrics["quota_usage_percentage"] = 0

        return metrics

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查条件"""
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "eq": lambda v, t: v == t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
        }
        return ops.get(condition, lambda v, t: False)(value, threshold)

    async def _is_in_cooldown(self, rule_name: str, tenant_id: Optional[str] = None) -> bool:
        """检查是否在冷却期"""
        key = f"alert:cooldown:{rule_name}:{tenant_id or 'global'}"
        return bool(await self.redis.get(key))

    async def _set_cooldown(self, rule_name: str, tenant_id: Optional[str], minutes: int):
        """设置冷却期"""
        key = f"alert:cooldown:{rule_name}:{tenant_id or 'global'}"
        await self.redis.setex(key, minutes * 60, "1")

    async def _send_alert(self, alert: Alert, channels: List[AlertChannel]):
        """发送告警"""
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self._send_email_alert(alert)
                elif channel == AlertChannel.SMS:
                    await self._send_sms_alert(alert)
                elif channel == AlertChannel.DINGTALK:
                    await self._send_dingtalk_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_alert(alert)
            except Exception as e:
                logger.error(f"发送告警失败 via {channel}: {e}")

    async def _send_email_alert(self, alert: Alert):
        """发送邮件告警"""
        try:
            recipients = self._get_alert_recipients(AlertChannel.EMAIL)
            if not recipients:
                return

            subject = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            body = f"""
告警规则: {alert.rule_name}
告警级别: {alert.severity.value.upper()}
告警消息: {alert.message}
触发时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
租户: {alert.tenant_id or '全局'}

指标值: {alert.metric_value}
阈值: {alert.threshold}
"""

            await self.notification_service.send_email(
                recipients=recipients, subject=subject, body=body
            )
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")

    async def _send_sms_alert(self, alert: Alert):
        """发送短信告警"""
        try:
            phones = self._get_alert_recipients(AlertChannel.SMS)
            if not phones:
                return

            message = f"[告警] {alert.message}"
            await self.notification_service.send_sms(phones=phones, message=message)
        except Exception as e:
            logger.error(f"发送短信告警失败: {e}")

    async def _send_dingtalk_alert(self, alert: Alert):
        """发送钉钉告警"""
        webhook_url = getattr(settings, "dingtalk_webhook_url", None)
        if not webhook_url:
            return

        color_map = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.ERROR: "#ff4d4f",
            AlertSeverity.CRITICAL: "#ff0000",
        }

        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"告警: {alert.rule_name}",
                "text": f"""### {alert.severity.value.upper()} 告警

**规则**: {alert.rule_name}

**消息**: {alert.message}

**时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

**租户**: {alert.tenant_id or '全局'}

**指标值**: {alert.metric_value}

**阈值**: {alert.threshold}
""",
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=message, timeout=10)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"发送钉钉告警失败: {e}")

    async def _send_slack_alert(self, alert: Alert):
        """发送Slack告警"""
        webhook_url = getattr(settings, "slack_webhook_url", None)
        if not webhook_url:
            return

        color_map = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.ERROR: "#ff4d4f",
            AlertSeverity.CRITICAL: "#ff0000",
        }

        message = {
            "text": f"告警: {alert.rule_name}",
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#000000"),
                    "fields": [
                        {"title": "规则", "value": alert.rule_name, "short": True},
                        {
                            "title": "级别",
                            "value": alert.severity.value.upper(),
                            "short": True,
                        },
                        {"title": "消息", "value": alert.message, "short": False},
                        {
                            "title": "租户",
                            "value": alert.tenant_id or "全局",
                            "short": True,
                        },
                        {
                            "title": "时间",
                            "value": alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True,
                        },
                    ],
                }
            ],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=message, timeout=10)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"发送Slack告警失败: {e}")

    async def _send_webhook_alert(self, alert: Alert):
        """发送Webhook告警"""
        webhook_url = getattr(settings, "alert_webhook_url", None)
        if not webhook_url:
            return

        payload = {
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "tenant_id": alert.tenant_id,
            "triggered_at": alert.triggered_at.isoformat(),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")

    def _get_alert_recipients(self, channel: AlertChannel) -> List[str]:
        """获取告警接收人"""
        # 从环境变量读取
        if channel == AlertChannel.EMAIL:
            recipients_str = getattr(settings, "alert_email_recipients", "")
            return [r.strip() for r in recipients_str.split(",") if r.strip()]
        elif channel == AlertChannel.SMS:
            phones_str = getattr(settings, "alert_sms_phones", "")
            return [p.strip() for p in phones_str.split(",") if p.strip()]
        return []

    async def _get_quota_usage(self, tenant_id: str) -> dict:
        """获取配额使用情况"""
        try:
            from services.quota_service import QuotaService
            from db import get_async_session

            async with get_async_session() as db:
                quota_service = QuotaService(db)
                return await quota_service.get_quota_status(tenant_id)
        except Exception as e:
            logger.error(f"获取配额使用情况失败: {e}")
            return {}

    # ==================== 规则管理 ====================

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.name] = rule

    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.rules:
            del self.rules[rule_name]

    def enable_rule(self, rule_name: str):
        """启用告警规则"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True

    def disable_rule(self, rule_name: str):
        """禁用告警规则"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False

    def get_rules(self) -> List[AlertRule]:
        """获取所有规则"""
        return list(self.rules.values())
