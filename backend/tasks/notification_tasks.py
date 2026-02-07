"""
通知相关的后台任务

支持：
- 邮件通知 (SMTP)
- 短信通知 (阿里云)
- 站内信通知
- Webhook通知
- 批量通知
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tasks.celery_app import celery_app
from db import get_async_session

logger = logging.getLogger(__name__)


def run_async(coro):
    """在同步环境中运行异步代码"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3)
def send_email_notification(
    self,
    recipient: str,
    subject: str,
    content: str,
    content_type: str = "html",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachment_name: Optional[str] = None,
    attachment_content: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    发送邮件通知

    Args:
        recipient: 收件人邮箱
        subject: 邮件主题
        content: 邮件内容
        content_type: 内容类型 (html/plain)
        cc: 抄送列表
        bcc: 密送列表
        attachment_name: 附件名称
        attachment_content: 附件内容

    Returns:
        发送结果
    """
    try:
        logger.info(f"发送邮件到 {recipient}: {subject}")

        async def _send():
            from services.notification_service import EmailService

            email_service = EmailService()

            attachments = None
            if attachment_name and attachment_content:
                attachments = [{
                    "name": attachment_name,
                    "content": attachment_content,
                }]

            return await email_service.send_email(
                to=recipient,
                subject=subject,
                content=content,
                content_type=content_type,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
            )

        result = run_async(_send())

        if result.get("success"):
            logger.info(f"邮件发送成功: to={recipient}")
            return result
        else:
            logger.error(f"邮件发送失败: {result.get('error')}")
            raise Exception(result.get("error", "邮件发送失败"))

    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        # 重试机制
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_sms_notification(
    self,
    phone: str,
    template_code: str,
    template_params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    发送短信通知

    Args:
        phone: 手机号
        template_code: 短信模板ID
        template_params: 模板参数

    Returns:
        发送结果
    """
    try:
        logger.info(f"发送短信到 {phone}, 模板: {template_code}")

        async def _send():
            from services.notification_service import SMSService

            sms_service = SMSService()
            return await sms_service.send_sms(
                phone=phone,
                template_code=template_code,
                template_params=template_params,
            )

        result = run_async(_send())

        if result.get("success"):
            logger.info(f"短信发送成功: phone={phone}")
            return result
        else:
            logger.error(f"短信发送失败: {result.get('error')}")
            raise Exception(result.get("error", "短信发送失败"))

    except Exception as e:
        logger.error(f"发送短信失败: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task
def send_in_app_notification(
    tenant_id: str,
    title: str,
    content: str,
    notification_type: str = "system",
    priority: str = "normal",
    link: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    发送站内通知

    Args:
        tenant_id: 租户ID
        title: 通知标题
        content: 通知内容
        notification_type: 通知类型 (system/billing/subscription/alert)
        priority: 优先级 (low/normal/high/urgent)
        link: 关联链接
        metadata: 元数据

    Returns:
        发送结果
    """
    try:
        logger.info(f"发送站内信: tenant={tenant_id}, title={title}")

        async def _send():
            async with get_async_session() as db:
                from services.notification_service import (
                    InAppNotificationService,
                    NotificationPriority,
                )

                service = InAppNotificationService(db)

                # 转换优先级
                priority_enum = NotificationPriority.NORMAL
                if priority == "low":
                    priority_enum = NotificationPriority.LOW
                elif priority == "high":
                    priority_enum = NotificationPriority.HIGH
                elif priority == "urgent":
                    priority_enum = NotificationPriority.URGENT

                return await service.send_notification(
                    tenant_id=tenant_id,
                    title=title,
                    content=content,
                    notification_type=notification_type,
                    priority=priority_enum,
                    link=link,
                    metadata=metadata,
                )

        result = run_async(_send())

        if result.get("success"):
            logger.info(f"站内信发送成功: tenant={tenant_id}")
        else:
            logger.warning(f"站内信发送失败: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"发送站内信失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task(bind=True, max_retries=3)
def send_webhook_notification(
    self,
    webhook_url: str,
    event_type: str,
    data: Dict[str, Any],
    secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    发送Webhook通知

    Args:
        webhook_url: Webhook URL
        event_type: 事件类型
        data: 事件数据
        secret: 签名密钥（可选）

    Returns:
        发送结果
    """
    try:
        import httpx
        import hmac
        import hashlib
        import json

        logger.info(f"发送Webhook通知: {event_type} -> {webhook_url}")

        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
        }

        # 如果提供了密钥，添加签名
        if secret:
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(
                secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # 发送请求
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload, headers=headers)

            if response.status_code < 400:
                logger.info(f"Webhook发送成功: {event_type}, status={response.status_code}")
                return {
                    "success": True,
                    "event": event_type,
                    "status_code": response.status_code,
                }
            else:
                logger.error(f"Webhook返回错误: status={response.status_code}")
                raise Exception(f"Webhook返回错误状态码: {response.status_code}")

    except Exception as e:
        logger.error(f"发送Webhook失败: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task
def send_multi_channel_notification(
    tenant_id: str,
    title: str,
    content: str,
    channels: List[str],
    email: Optional[str] = None,
    phone: Optional[str] = None,
    sms_template: Optional[str] = None,
    sms_params: Optional[Dict[str, str]] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    多渠道通知

    Args:
        tenant_id: 租户ID
        title: 通知标题
        content: 通知内容
        channels: 通知渠道列表 (email/sms/in_app)
        email: 收件人邮箱
        phone: 手机号
        sms_template: 短信模板ID
        sms_params: 短信模板参数
        priority: 优先级
        metadata: 元数据

    Returns:
        各渠道发送结果
    """
    logger.info(f"发送多渠道通知: tenant={tenant_id}, channels={channels}")

    results = {
        "tenant_id": tenant_id,
        "channels": {},
    }

    # 邮件通知
    if "email" in channels and email:
        try:
            send_email_notification.delay(
                recipient=email,
                subject=title,
                content=content,
            )
            results["channels"]["email"] = {"queued": True}
        except Exception as e:
            results["channels"]["email"] = {"error": str(e)}

    # 短信通知
    if "sms" in channels and phone and sms_template:
        try:
            send_sms_notification.delay(
                phone=phone,
                template_code=sms_template,
                template_params=sms_params,
            )
            results["channels"]["sms"] = {"queued": True}
        except Exception as e:
            results["channels"]["sms"] = {"error": str(e)}

    # 站内信通知
    if "in_app" in channels:
        try:
            send_in_app_notification.delay(
                tenant_id=tenant_id,
                title=title,
                content=content,
                priority=priority,
                metadata=metadata,
            )
            results["channels"]["in_app"] = {"queued": True}
        except Exception as e:
            results["channels"]["in_app"] = {"error": str(e)}

    return results


@celery_app.task
def batch_send_notifications(
    notification_type: str,
    recipients: List[Dict[str, Any]],
    content: Dict[str, Any],
) -> Dict[str, Any]:
    """
    批量发送通知

    Args:
        notification_type: 通知类型 (email/sms/in_app)
        recipients: 收件人列表 [{email/phone/tenant_id, ...}]
        content: 通知内容 {subject, body, template_code, template_params, ...}

    Returns:
        批量发送结果
    """
    logger.info(f"批量发送 {notification_type} 通知给 {len(recipients)} 个收件人")

    results = {
        "total": len(recipients),
        "queued": 0,
        "failed": 0,
        "errors": [],
    }

    for recipient in recipients:
        try:
            if notification_type == "email":
                email = recipient.get("email")
                if email:
                    send_email_notification.delay(
                        recipient=email,
                        subject=content.get("subject", ""),
                        content=content.get("body", ""),
                    )
                    results["queued"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "recipient": recipient,
                        "error": "缺少email字段",
                    })

            elif notification_type == "sms":
                phone = recipient.get("phone")
                template_code = content.get("template_code")
                if phone and template_code:
                    send_sms_notification.delay(
                        phone=phone,
                        template_code=template_code,
                        template_params=content.get("template_params", {}),
                    )
                    results["queued"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "recipient": recipient,
                        "error": "缺少phone或template_code",
                    })

            elif notification_type == "in_app":
                tenant_id = recipient.get("tenant_id")
                if tenant_id:
                    send_in_app_notification.delay(
                        tenant_id=tenant_id,
                        title=content.get("title", ""),
                        content=content.get("body", ""),
                        notification_type=content.get("notification_type", "system"),
                        priority=content.get("priority", "normal"),
                    )
                    results["queued"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "recipient": recipient,
                        "error": "缺少tenant_id字段",
                    })

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "recipient": recipient,
                "error": str(e),
            })

    return results


# ===== 业务通知快捷方法 =====

@celery_app.task
def notify_subscription_expiring(
    tenant_id: str,
    email: Optional[str],
    phone: Optional[str],
    days_left: int,
    plan_type: str,
    expire_date: str,
) -> Dict[str, Any]:
    """
    发送订阅即将到期通知

    Args:
        tenant_id: 租户ID
        email: 邮箱
        phone: 手机号
        days_left: 剩余天数
        plan_type: 套餐类型
        expire_date: 到期日期

    Returns:
        发送结果
    """
    from services.notification_service import NotificationTemplates

    template = NotificationTemplates.subscription_expiring(
        days_left=days_left,
        plan_type=plan_type,
        expire_date=expire_date,
    )

    channels = ["in_app"]
    if email:
        channels.append("email")
    if phone and days_left <= 3:  # 剩余3天内才发短信
        channels.append("sms")

    return send_multi_channel_notification.delay(
        tenant_id=tenant_id,
        title=template["title"],
        content=template["content"],
        channels=channels,
        email=email,
        phone=phone,
        sms_template=template.get("sms_template"),
        sms_params=template.get("sms_params"),
        priority="high" if days_left <= 1 else "normal",
    )


@celery_app.task
def notify_subscription_expired(
    tenant_id: str,
    email: Optional[str],
    phone: Optional[str],
    plan_type: str,
) -> Dict[str, Any]:
    """
    发送订阅已过期通知

    Args:
        tenant_id: 租户ID
        email: 邮箱
        phone: 手机号
        plan_type: 套餐类型

    Returns:
        发送结果
    """
    from services.notification_service import NotificationTemplates

    template = NotificationTemplates.subscription_expired(plan_type=plan_type)

    channels = ["in_app"]
    if email:
        channels.append("email")
    if phone:
        channels.append("sms")

    return send_multi_channel_notification.delay(
        tenant_id=tenant_id,
        title=template["title"],
        content=template["content"],
        channels=channels,
        email=email,
        phone=phone,
        sms_template=template.get("sms_template"),
        sms_params=template.get("sms_params"),
        priority="urgent",
    )


@celery_app.task
def notify_payment_success(
    tenant_id: str,
    email: Optional[str],
    order_number: str,
    amount: float,
    plan_type: str,
) -> Dict[str, Any]:
    """
    发送支付成功通知

    Args:
        tenant_id: 租户ID
        email: 邮箱
        order_number: 订单号
        amount: 金额
        plan_type: 套餐类型

    Returns:
        发送结果
    """
    from services.notification_service import NotificationTemplates

    template = NotificationTemplates.payment_success(
        order_number=order_number,
        amount=amount,
        plan_type=plan_type,
    )

    channels = ["in_app"]
    if email:
        channels.append("email")

    return send_multi_channel_notification.delay(
        tenant_id=tenant_id,
        title=template["title"],
        content=template["content"],
        channels=channels,
        email=email,
        priority="normal",
    )


@celery_app.task
def notify_quota_warning(
    tenant_id: str,
    email: Optional[str],
    quota_type: str,
    used: int,
    total: int,
    percentage: int,
) -> Dict[str, Any]:
    """
    发送配额预警通知

    Args:
        tenant_id: 租户ID
        email: 邮箱
        quota_type: 配额类型
        used: 已使用量
        total: 总配额
        percentage: 使用百分比

    Returns:
        发送结果
    """
    from services.notification_service import NotificationTemplates

    template = NotificationTemplates.quota_warning(
        quota_type=quota_type,
        used=used,
        total=total,
        percentage=percentage,
    )

    channels = ["in_app"]
    if email and percentage >= 90:  # 90%以上才发邮件
        channels.append("email")

    return send_multi_channel_notification.delay(
        tenant_id=tenant_id,
        title=template["title"],
        content=template["content"],
        channels=channels,
        email=email,
        priority="high" if percentage >= 95 else "normal",
    )
