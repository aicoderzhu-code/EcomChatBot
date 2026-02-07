"""
安全审计日志服务
"""
from typing import Optional, Any
from datetime import datetime
import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class SecurityLogger:
    """安全审计日志记录器"""

    def __init__(self, db: AsyncSession):
        """
        初始化安全日志记录器

        Args:
            db: 数据库会话
        """
        self.db = db

    async def log(
        self,
        event_type: AuditEventType | str,
        message: str,
        *,
        severity: AuditSeverity = AuditSeverity.INFO,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        admin_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        actor_name: Optional[str] = None,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        记录安全审计日志

        Args:
            event_type: 事件类型
            message: 日志消息
            severity: 严重程度
            tenant_id: 租户ID
            user_id: 用户ID
            admin_id: 管理员ID
            actor_type: 操作者类型（tenant/admin/system）
            actor_name: 操作者名称
            request: FastAPI Request 对象
            request_id: 请求ID
            ip_address: IP地址
            user_agent: 用户代理
            resource_type: 资源类型
            resource_id: 资源ID
            action: 操作类型
            success: 是否成功
            error_message: 错误消息
            metadata: 额外元数据
        """
        try:
            # 从 Request 对象提取信息
            if request:
                if not ip_address:
                    ip_address = self._get_client_ip(request)
                if not user_agent:
                    user_agent = request.headers.get("user-agent")
                if not request_id:
                    request_id = request.state.__dict__.get("request_id")

            # 创建审计日志
            audit_log = AuditLog(
                event_type=event_type if isinstance(event_type, str) else event_type.value,
                severity=severity if isinstance(severity, str) else severity.value,
                message=message,
                tenant_id=tenant_id,
                user_id=user_id,
                admin_id=admin_id,
                actor_type=actor_type,
                actor_name=actor_name,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                success="true" if success else "false",
                error_message=error_message,
                metadata=metadata,
            )

            self.db.add(audit_log)
            await self.db.commit()

            # 如果是严重事件，同时记录到应用日志
            if severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
                logger.warning(
                    f"Security Event: {event_type} - {message} "
                    f"(tenant: {tenant_id}, ip: {ip_address})"
                )

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            # 审计日志失败不应影响主流程
            await self.db.rollback()

    # ==================== 认证事件 ====================

    async def log_login_success(
        self,
        tenant_id: str,
        request: Request,
        actor_name: str = None,
    ):
        """记录登录成功"""
        await self.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            message=f"用户 {actor_name or tenant_id} 登录成功",
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            actor_type="tenant",
            actor_name=actor_name,
            request=request,
            action="login",
            success=True,
        )

    async def log_login_failed(
        self,
        request: Request,
        reason: str,
        attempted_email: str = None,
    ):
        """记录登录失败"""
        await self.log(
            event_type=AuditEventType.LOGIN_FAILED,
            message=f"登录失败: {reason}",
            severity=AuditSeverity.WARNING,
            request=request,
            action="login",
            success=False,
            error_message=reason,
            metadata={"attempted_email": attempted_email},
        )

    async def log_logout(
        self,
        tenant_id: str,
        request: Request,
    ):
        """记录登出"""
        await self.log(
            event_type=AuditEventType.LOGOUT,
            message="用户登出",
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            actor_type="tenant",
            request=request,
            action="logout",
            success=True,
        )

    # ==================== 权限事件 ====================

    async def log_permission_denied(
        self,
        tenant_id: Optional[str],
        admin_id: Optional[str],
        permission: str,
        request: Request,
    ):
        """记录权限拒绝"""
        await self.log(
            event_type=AuditEventType.PERMISSION_DENIED,
            message=f"权限被拒绝: {permission}",
            severity=AuditSeverity.WARNING,
            tenant_id=tenant_id,
            admin_id=admin_id,
            actor_type="admin" if admin_id else "tenant",
            request=request,
            action="permission_check",
            success=False,
            metadata={"required_permission": permission},
        )

    async def log_role_changed(
        self,
        admin_id: str,
        old_role: str,
        new_role: str,
        changed_by: str,
    ):
        """记录角色变更"""
        await self.log(
            event_type=AuditEventType.ROLE_CHANGED,
            message=f"管理员角色从 {old_role} 变更为 {new_role}",
            severity=AuditSeverity.INFO,
            admin_id=admin_id,
            actor_type="admin",
            action="role_change",
            success=True,
            metadata={
                "old_role": old_role,
                "new_role": new_role,
                "changed_by": changed_by,
            },
        )

    # ==================== 租户事件 ====================

    async def log_tenant_created(
        self,
        tenant_id: str,
        company_name: str,
        request: Request,
    ):
        """记录租户创建"""
        await self.log(
            event_type=AuditEventType.TENANT_CREATED,
            message=f"新租户创建: {company_name}",
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            actor_type="system",
            request=request,
            resource_type="tenant",
            resource_id=tenant_id,
            action="create",
            success=True,
        )

    async def log_tenant_suspended(
        self,
        tenant_id: str,
        reason: str,
        admin_id: str,
    ):
        """记录租户暂停"""
        await self.log(
            event_type=AuditEventType.TENANT_SUSPENDED,
            message=f"租户被暂停: {reason}",
            severity=AuditSeverity.WARNING,
            tenant_id=tenant_id,
            admin_id=admin_id,
            actor_type="admin",
            resource_type="tenant",
            resource_id=tenant_id,
            action="suspend",
            success=True,
            metadata={"reason": reason},
        )

    # ==================== 安全事件 ====================

    async def log_suspicious_activity(
        self,
        request: Request,
        description: str,
        tenant_id: Optional[str] = None,
    ):
        """记录可疑活动"""
        await self.log(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            message=f"检测到可疑活动: {description}",
            severity=AuditSeverity.ERROR,
            tenant_id=tenant_id,
            request=request,
            action="security_check",
            success=False,
            metadata={"description": description},
        )

    async def log_rate_limit_exceeded(
        self,
        request: Request,
        limit: int,
        window: str,
        tenant_id: Optional[str] = None,
    ):
        """记录速率限制超出"""
        await self.log(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            message=f"速率限制超出: {limit} 次/{window}",
            severity=AuditSeverity.WARNING,
            tenant_id=tenant_id,
            request=request,
            action="rate_limit_check",
            success=False,
            metadata={"limit": limit, "window": window},
        )

    async def log_xss_attempt(
        self,
        request: Request,
        field: str,
        content_preview: str,
        tenant_id: Optional[str] = None,
    ):
        """记录 XSS 攻击尝试"""
        await self.log(
            event_type=AuditEventType.XSS_ATTEMPT_BLOCKED,
            message=f"XSS 攻击尝试被阻止 (字段: {field})",
            severity=AuditSeverity.ERROR,
            tenant_id=tenant_id,
            request=request,
            action="xss_check",
            success=False,
            metadata={
                "field": field,
                "content_preview": content_preview[:100],  # 只记录前100个字符
            },
        )

    async def log_sql_injection_attempt(
        self,
        request: Request,
        field: str,
        content_preview: str,
        tenant_id: Optional[str] = None,
    ):
        """记录 SQL 注入攻击尝试"""
        await self.log(
            event_type=AuditEventType.SQL_INJECTION_ATTEMPT,
            message=f"SQL 注入攻击尝试被阻止 (字段: {field})",
            severity=AuditSeverity.CRITICAL,
            tenant_id=tenant_id,
            request=request,
            action="sql_injection_check",
            success=False,
            metadata={
                "field": field,
                "content_preview": content_preview[:100],
            },
        )

    async def log_account_locked(
        self,
        tenant_id: str,
        reason: str,
    ):
        """记录账户锁定"""
        await self.log(
            event_type=AuditEventType.ACCOUNT_LOCKED,
            message=f"账户被锁定: {reason}",
            severity=AuditSeverity.WARNING,
            tenant_id=tenant_id,
            actor_type="system",
            resource_type="tenant",
            resource_id=tenant_id,
            action="lock",
            success=True,
            metadata={"reason": reason},
        )

    # ==================== 工具方法 ====================

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        获取客户端真实IP地址

        考虑反向代理（Nginx等）设置的头部
        """
        # 尝试从 X-Forwarded-For 获取
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 尝试从 X-Real-IP 获取
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 直接连接的IP
        if request.client:
            return request.client.host

        return "unknown"


# ==================== 全局实例 ====================


# 用于不需要数据库会话的场景（记录到日志文件）
def log_security_event_to_file(
    event_type: str,
    message: str,
    severity: str = "INFO",
    **kwargs: Any
):
    """
    记录安全事件到文件（备份方案）

    当数据库不可用时使用
    """
    log_level = {
        AuditSeverity.INFO: logging.INFO,
        AuditSeverity.WARNING: logging.WARNING,
        AuditSeverity.ERROR: logging.ERROR,
        AuditSeverity.CRITICAL: logging.CRITICAL,
    }.get(severity, logging.INFO)

    logger.log(
        log_level,
        f"Security Event: {event_type} - {message}",
        extra=kwargs
    )