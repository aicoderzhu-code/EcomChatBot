"""
安全审计日志模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid

from models.base import Base


class AuditEventType(str, Enum):
    """审计事件类型"""

    # 认证相关
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGED = "password_changed"
    API_KEY_GENERATED = "api_key_generated"
    API_KEY_REVOKED = "api_key_revoked"

    # 授权相关
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"

    # 资源访问
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_ACCESSED = "resource_accessed"
    RESOURCE_ACCESS_DENIED = "resource_access_denied"

    # 租户管理
    TENANT_CREATED = "tenant_created"
    TENANT_SUSPENDED = "tenant_suspended"
    TENANT_ACTIVATED = "tenant_activated"
    TENANT_DELETED = "tenant_deleted"
    TENANT_CONFIG_CHANGED = "tenant_config_changed"

    # 订阅和计费
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"

    # 配额管理
    QUOTA_ADJUSTED = "quota_adjusted"
    QUOTA_EXCEEDED = "quota_exceeded"
    QUOTA_WARNING = "quota_warning"

    # 安全事件
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CSRF_TOKEN_INVALID = "csrf_token_invalid"
    XSS_ATTEMPT_BLOCKED = "xss_attempt_blocked"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"

    # 系统事件
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    DATABASE_BACKUP = "database_backup"
    MIGRATION_EXECUTED = "migration_executed"


class AuditSeverity(str, Enum):
    """审计事件严重程度"""

    INFO = "info"          # 一般信息
    WARNING = "warning"    # 警告
    ERROR = "error"        # 错误
    CRITICAL = "critical"  # 严重


class AuditLog(Base):
    """安全审计日志"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 事件信息
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default=AuditSeverity.INFO)
    message = Column(Text, nullable=False)

    # 主体信息（谁）
    tenant_id = Column(UUID(as_uuid=True), index=True)  # 租户ID
    user_id = Column(UUID(as_uuid=True), index=True)    # 用户ID（可选）
    admin_id = Column(UUID(as_uuid=True), index=True)   # 管理员ID（可选）
    actor_type = Column(String(20))  # tenant/admin/system
    actor_name = Column(String(255))  # 操作者名称

    # 请求信息（从哪里）
    ip_address = Column(INET)  # IP地址
    user_agent = Column(Text)  # 用户代理
    request_id = Column(String(50), index=True)  # 请求ID（用于关联）

    # 资源信息（对什么）
    resource_type = Column(String(50))  # 资源类型（如：conversation, tenant）
    resource_id = Column(String(50))    # 资源ID
    action = Column(String(50))         # 操作类型（create/read/update/delete）

    # 结果信息
    success = Column(String(10), nullable=False)  # true/false
    error_message = Column(Text)  # 失败原因

    # 额外数据（JSON格式）
    metadata = Column(JSON)  # 额外的上下文信息

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_audit_logs_tenant_created', 'tenant_id', 'created_at'),
        Index('idx_audit_logs_event_created', 'event_type', 'created_at'),
        Index('idx_audit_logs_severity_created', 'severity', 'created_at'),
        Index('idx_audit_logs_success', 'success'),
        Index('idx_audit_logs_ip', 'ip_address'),
    )

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, event_type={self.event_type}, "
            f"severity={self.severity}, tenant_id={self.tenant_id})>"
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "admin_id": str(self.admin_id) if self.admin_id else None,
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }