"""
管理员表模型
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class Admin(BaseModel):
    """管理员表"""

    __tablename__ = "platform_admins"
    __table_args__ = (
        Index("idx_admin_username", "username"),
        Index("idx_admin_email", "email"),
        Index("idx_admin_role", "role"),
        Index("idx_admin_status", "status"),
        {"comment": "平台管理员表"},
    )

    # 基础字段
    admin_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="管理员唯一标识"
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="用户名"
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    email: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="邮箱"
    )
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")

    # 角色与权限
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="viewer",
        comment="角色(super_admin/finance_admin/support_admin/viewer)",
    )
    permissions: Mapped[list | None] = mapped_column(
        JSON, comment="权限列表(JSON格式，用于细粒度权限控制)"
    )

    # 状态字段
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", comment="状态(active/suspended/deleted)"
    )

    # 安全字段
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后登录时间")
    last_login_ip: Mapped[str | None] = mapped_column(String(64), comment="最后登录IP")
    login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="登录尝试次数"
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, comment="账号锁定到期时间")

    # 审计字段
    created_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")

    def __repr__(self) -> str:
        return f"<Admin {self.username} ({self.role})>"


class AdminOperationLog(BaseModel):
    """管理员操作日志表"""

    __tablename__ = "admin_operation_logs"
    __table_args__ = (
        Index("idx_operation_admin", "admin_id"),
        Index("idx_operation_resource", "resource_type", "resource_id"),
        Index("idx_operation_created", "created_at"),
        {"comment": "管理员操作日志表"},
    )

    # 操作信息
    admin_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作管理员ID")
    operation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="操作类型(create/update/delete/suspend/grant等)"
    )

    # 资源信息
    resource_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="资源类型(tenant/subscription/quota/bill等)"
    )
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="资源ID")

    # 操作详情
    operation_details: Mapped[dict | None] = mapped_column(JSON, comment="操作详情")
    before_value: Mapped[dict | None] = mapped_column(JSON, comment="变更前的值")
    after_value: Mapped[dict | None] = mapped_column(JSON, comment="变更后的值")

    # 请求信息
    ip_address: Mapped[str | None] = mapped_column(String(64), comment="操作IP")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")

    # 执行结果
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="success", comment="状态(success/failed)"
    )
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")

    def __repr__(self) -> str:
        return f"<AdminOperationLog {self.operation_type} on {self.resource_type}>"


class PermissionTemplate(BaseModel):
    """权限模板表"""

    __tablename__ = "permission_templates"
    __table_args__ = (
        Index("idx_template_name", "template_name"),
        {"comment": "权限模板表"},
    )

    # 模板信息
    template_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="模板ID"
    )
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    description: Mapped[str | None] = mapped_column(Text, comment="模板描述")

    # 功能模块
    enabled_features: Mapped[list] = mapped_column(
        JSON, nullable=False, comment="开通的功能模块(JSON数组)"
    )

    # 配额配置
    quota_config: Mapped[dict] = mapped_column(JSON, nullable=False, comment="配额配置(JSON对象)")

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="是否启用"
    )

    # 创建人
    created_by: Mapped[str | None] = mapped_column(String(64), comment="创建人")

    def __repr__(self) -> str:
        return f"<PermissionTemplate {self.template_name}>"
