"""
通知服务

支持多种通知渠道：
- 邮件 (SMTP/阿里云邮件)
- 短信 (阿里云短信)
- 站内信 (数据库存储)
"""
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailService:
    """邮件服务"""

    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "smtp.example.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 465)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.smtp_ssl = getattr(settings, "SMTP_SSL", True)
        self.from_email = getattr(settings, "EMAIL_FROM", "noreply@example.com")
        self.from_name = getattr(settings, "EMAIL_FROM_NAME", "智能客服系统")

    async def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        content_type: str = "html",
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        发送邮件

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型 (html/plain)
            cc: 抄送列表
            bcc: 密送列表
            attachments: 附件列表 [{name, content, content_type}]

        Returns:
            发送结果
        """
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders

            # 构建邮件
            if attachments:
                msg = MIMEMultipart()
                msg.attach(MIMEText(content, content_type, "utf-8"))

                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.get("content", b""))
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment.get('name', 'attachment')}",
                    )
                    msg.attach(part)
            else:
                msg = MIMEText(content, content_type, "utf-8")

            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to

            if cc:
                msg["Cc"] = ", ".join(cc)
            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            # 发送邮件
            if self.smtp_ssl:
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password,
                    use_tls=True,
                )
            else:
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password,
                    start_tls=True,
                )

            logger.info(f"邮件发送成功: to={to}, subject={subject}")

            return {
                "success": True,
                "to": to,
                "subject": subject,
            }

        except ImportError:
            logger.warning("aiosmtplib未安装，邮件发送跳过")
            return {
                "success": False,
                "error": "aiosmtplib未安装",
            }
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class SMSService:
    """短信服务（阿里云）"""

    def __init__(self):
        self.access_key_id = getattr(settings, "ALIYUN_ACCESS_KEY_ID", "")
        self.access_key_secret = getattr(settings, "ALIYUN_ACCESS_KEY_SECRET", "")
        self.sign_name = getattr(settings, "ALIYUN_SMS_SIGN_NAME", "智能客服")
        self.region_id = getattr(settings, "ALIYUN_SMS_REGION", "cn-hangzhou")

    async def send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        发送短信

        Args:
            phone: 手机号
            template_code: 短信模板ID
            template_params: 模板参数

        Returns:
            发送结果
        """
        try:
            from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
            from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
            from alibabacloud_tea_openapi import models as open_api_models
            import json

            if not self.access_key_id or not self.access_key_secret:
                logger.warning("阿里云短信配置不完整，跳过发送")
                return {
                    "success": False,
                    "error": "短信配置不完整",
                }

            # 创建客户端
            config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
            )
            config.endpoint = f"dysmsapi.aliyuncs.com"
            client = Dysmsapi20170525Client(config)

            # 构建请求
            send_request = dysmsapi_20170525_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.sign_name,
                template_code=template_code,
                template_param=json.dumps(template_params) if template_params else None,
            )

            # 发送短信
            response = client.send_sms(send_request)

            if response.body.code == "OK":
                logger.info(f"短信发送成功: phone={phone}, template={template_code}")
                return {
                    "success": True,
                    "phone": phone,
                    "biz_id": response.body.biz_id,
                }
            else:
                logger.error(f"短信发送失败: {response.body.message}")
                return {
                    "success": False,
                    "error": response.body.message,
                    "code": response.body.code,
                }

        except ImportError:
            logger.warning("alibabacloud-dysmsapi20170525未安装，短信发送跳过")
            return {
                "success": False,
                "error": "阿里云SDK未安装",
            }
        except Exception as e:
            logger.error(f"短信发送失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class InAppNotificationService:
    """站内信服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_notification(
        self,
        tenant_id: str,
        title: str,
        content: str,
        notification_type: str = "system",
        priority: NotificationPriority = NotificationPriority.NORMAL,
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
            priority: 优先级
            link: 关联链接
            metadata: 元数据

        Returns:
            发送结果
        """
        try:
            # 尝试导入站内信模型
            try:
                from models.notification import InAppNotification
            except ImportError:
                # 如果模型不存在，记录日志并返回
                logger.warning("InAppNotification模型不存在，跳过站内信发送")
                return {
                    "success": False,
                    "error": "站内信功能未启用",
                }

            notification = InAppNotification(
                tenant_id=tenant_id,
                title=title,
                content=content,
                notification_type=notification_type,
                priority=priority.value,
                link=link,
                metadata=metadata or {},
                is_read=False,
            )

            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)

            logger.info(f"站内信发送成功: tenant={tenant_id}, title={title}")

            return {
                "success": True,
                "notification_id": notification.id,
                "tenant_id": tenant_id,
            }

        except Exception as e:
            logger.error(f"站内信发送失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_notifications(
        self,
        tenant_id: str,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取站内通知列表

        Args:
            tenant_id: 租户ID
            unread_only: 仅获取未读
            offset: 偏移量
            limit: 数量限制

        Returns:
            通知列表
        """
        try:
            from models.notification import InAppNotification

            stmt = select(InAppNotification).where(
                InAppNotification.tenant_id == tenant_id
            )

            if unread_only:
                stmt = stmt.where(InAppNotification.is_read == False)

            stmt = stmt.order_by(InAppNotification.created_at.desc()).offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            notifications = result.scalars().all()

            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "content": n.content,
                    "type": n.notification_type,
                    "priority": n.priority,
                    "link": n.link,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ]

        except ImportError:
            return []
        except Exception as e:
            logger.error(f"获取站内信失败: {e}")
            return []

    async def mark_as_read(
        self,
        tenant_id: str,
        notification_ids: Optional[List[int]] = None,
        mark_all: bool = False,
    ) -> int:
        """
        标记通知为已读

        Args:
            tenant_id: 租户ID
            notification_ids: 通知ID列表
            mark_all: 标记全部已读

        Returns:
            更新数量
        """
        try:
            from models.notification import InAppNotification

            if mark_all:
                stmt = (
                    update(InAppNotification)
                    .where(
                        and_(
                            InAppNotification.tenant_id == tenant_id,
                            InAppNotification.is_read == False,
                        )
                    )
                    .values(is_read=True, read_at=datetime.utcnow())
                )
            elif notification_ids:
                stmt = (
                    update(InAppNotification)
                    .where(
                        and_(
                            InAppNotification.tenant_id == tenant_id,
                            InAppNotification.id.in_(notification_ids),
                            InAppNotification.is_read == False,
                        )
                    )
                    .values(is_read=True, read_at=datetime.utcnow())
                )
            else:
                return 0

            result = await self.db.execute(stmt)
            await self.db.commit()

            return result.rowcount

        except ImportError:
            return 0
        except Exception as e:
            logger.error(f"标记已读失败: {e}")
            return 0


class NotificationService:
    """统一通知服务"""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.email_service = EmailService()
        self.sms_service = SMSService()
        self.in_app_service = InAppNotificationService(db) if db else None

    async def send(
        self,
        channels: List[NotificationType],
        tenant_id: str,
        title: str,
        content: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        sms_template: Optional[str] = None,
        sms_params: Optional[Dict[str, str]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送多渠道通知

        Args:
            channels: 通知渠道列表
            tenant_id: 租户ID
            title: 通知标题
            content: 通知内容
            email: 收件人邮箱（邮件通知必须）
            phone: 手机号（短信通知必须）
            sms_template: 短信模板ID
            sms_params: 短信模板参数
            priority: 优先级
            metadata: 元数据

        Returns:
            各渠道发送结果
        """
        results = {
            "tenant_id": tenant_id,
            "channels": {},
        }

        for channel in channels:
            if channel == NotificationType.EMAIL and email:
                result = await self.email_service.send_email(
                    to=email,
                    subject=title,
                    content=content,
                )
                results["channels"]["email"] = result

            elif channel == NotificationType.SMS and phone and sms_template:
                result = await self.sms_service.send_sms(
                    phone=phone,
                    template_code=sms_template,
                    template_params=sms_params,
                )
                results["channels"]["sms"] = result

            elif channel == NotificationType.IN_APP and self.in_app_service:
                result = await self.in_app_service.send_notification(
                    tenant_id=tenant_id,
                    title=title,
                    content=content,
                    priority=priority,
                    metadata=metadata,
                )
                results["channels"]["in_app"] = result

        # 计算整体成功状态
        all_success = all(
            r.get("success", False)
            for r in results["channels"].values()
        )
        results["success"] = all_success

        return results


# ===== 通知模板 =====

class NotificationTemplates:
    """通知模板"""

    @staticmethod
    def subscription_expiring(days_left: int, plan_type: str, expire_date: str) -> Dict[str, str]:
        """订阅即将到期模板"""
        return {
            "title": f"订阅将在{days_left}天后到期",
            "content": f"""
                <h2>订阅即将到期提醒</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的 <strong>{plan_type}</strong> 套餐将于 <strong>{expire_date}</strong> 到期。</p>
                <p>为避免服务中断，请及时续费。</p>
                <p>如有问题，请联系客服。</p>
            """,
            "sms_template": "SMS_SUBSCRIPTION_EXPIRING",
            "sms_params": {
                "days": str(days_left),
                "plan": plan_type,
            },
        }

    @staticmethod
    def subscription_expired(plan_type: str) -> Dict[str, str]:
        """订阅已过期模板"""
        return {
            "title": "订阅已过期",
            "content": f"""
                <h2>订阅已过期通知</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的 <strong>{plan_type}</strong> 套餐已过期，账户已自动降级为免费套餐。</p>
                <p>部分功能将受到限制，请及时续费以恢复全部功能。</p>
                <p>如有问题，请联系客服。</p>
            """,
            "sms_template": "SMS_SUBSCRIPTION_EXPIRED",
            "sms_params": {
                "plan": plan_type,
            },
        }

    @staticmethod
    def payment_success(order_number: str, amount: float, plan_type: str) -> Dict[str, str]:
        """支付成功模板"""
        return {
            "title": "支付成功",
            "content": f"""
                <h2>支付成功通知</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的订单 <strong>{order_number}</strong> 已支付成功。</p>
                <ul>
                    <li>订单金额：¥{amount:.2f}</li>
                    <li>套餐类型：{plan_type}</li>
                </ul>
                <p>套餐已立即生效，感谢您的信任！</p>
            """,
            "sms_template": "SMS_PAYMENT_SUCCESS",
            "sms_params": {
                "order": order_number,
                "amount": f"{amount:.2f}",
            },
        }

    @staticmethod
    def quota_warning(quota_type: str, used: int, total: int, percentage: int) -> Dict[str, str]:
        """配额预警模板"""
        return {
            "title": f"{quota_type}配额预警",
            "content": f"""
                <h2>配额使用预警</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的 <strong>{quota_type}</strong> 配额使用已达 <strong>{percentage}%</strong>。</p>
                <ul>
                    <li>已使用：{used}</li>
                    <li>配额上限：{total}</li>
                </ul>
                <p>请注意控制使用量，或考虑升级套餐以获得更多配额。</p>
            """,
            "sms_template": "SMS_QUOTA_WARNING",
            "sms_params": {
                "type": quota_type,
                "percentage": str(percentage),
            },
        }

    @staticmethod
    def refund_success(order_number: str, amount: float, reason: str) -> Dict[str, str]:
        """退款成功模板"""
        return {
            "title": "退款成功",
            "content": f"""
                <h2>退款成功通知</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的订单 <strong>{order_number}</strong> 退款已处理成功。</p>
                <ul>
                    <li>退款金额：¥{amount:.2f}</li>
                    <li>退款原因：{reason}</li>
                </ul>
                <p>退款将在1-7个工作日内原路返回至您的支付账户。</p>
            """,
            "sms_template": "SMS_REFUND_SUCCESS",
            "sms_params": {
                "order": order_number,
                "amount": f"{amount:.2f}",
            },
        }
