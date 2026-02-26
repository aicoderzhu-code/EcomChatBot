"""
对话相关模型
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import TenantBaseModel


class User(TenantBaseModel):
    """用户表"""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_user_tenant_external", "tenant_id", "user_external_id", unique=True),
        Index("idx_user_email", "email"),
        {"comment": "终端用户表"},
    )

    # 用户标识
    user_external_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户外部ID(租户内唯一)"
    )
    platform_user_id: Mapped[str | None] = mapped_column(
        String(128), comment="平台侧用户ID(如拼多多买家ID)"
    )

    # 基本信息
    nickname: Mapped[str | None] = mapped_column(String(128), comment="昵称")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), comment="邮箱")
    avatar: Mapped[str | None] = mapped_column(String(512), comment="头像URL")

    # VIP 等级
    vip_level: Mapped[int] = mapped_column(Integer, default=0, comment="VIP等级")

    # 用户画像
    profile: Mapped[dict | None] = mapped_column(
        Text, comment="用户画像(JSON格式: 购买历史、偏好等)"
    )

    # 统计信息
    total_conversations: Mapped[int] = mapped_column(
        Integer, default=0, comment="总对话次数"
    )
    last_conversation_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="最后对话时间"
    )

    # 关联关系
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.user_external_id}>"


class Conversation(TenantBaseModel):
    """会话表"""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversation_id", "conversation_id", unique=True),
        Index("idx_conversation_tenant", "tenant_id"),
        Index("idx_conversation_user", "tenant_id", "user_id"),
        Index("idx_conversation_status", "status"),
        Index("idx_conv_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("idx_conv_tenant_resolved", "tenant_id", "resolved"),
        {"comment": "会话表"},
    )

    # 会话标识
    conversation_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="会话ID"
    )

    # 用户信息
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")

    # 渠道信息
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, default="web", comment="渠道(web/mobile/api等)"
    )

    # 平台对接字段
    platform_type: Mapped[str | None] = mapped_column(
        String(32), comment="来源平台(pinduoduo等)"
    )
    platform_conversation_id: Mapped[str | None] = mapped_column(
        String(128), comment="平台侧会话ID"
    )

    # 会话状态
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", comment="状态(active/closed)"
    )

    # 时间信息
    start_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment="开始时间"
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime, comment="结束时间")

    # 满意度
    satisfaction_score: Mapped[int | None] = mapped_column(
        Integer, comment="满意度评分(1-5分)"
    )
    feedback: Mapped[str | None] = mapped_column(Text, comment="用户反馈")

    # 解决率相关字段
    resolved: Mapped[bool] = mapped_column(
        Integer, default=False, comment="是否解决问题"
    )
    resolution_type: Mapped[str | None] = mapped_column(
        String(20), comment="解决方式(ai/human/timeout/abandoned)"
    )
    transferred_to_human: Mapped[bool] = mapped_column(
        Integer, default=False, comment="是否转人工"
    )
    transfer_reason: Mapped[str | None] = mapped_column(
        String(255), comment="转人工原因"
    )
    resolution_time: Mapped[int | None] = mapped_column(
        Integer, comment="解决时长(秒)"
    )

    # 用量统计
    message_count: Mapped[int] = mapped_column(Integer, default=0, comment="消息数")
    token_usage: Mapped[int] = mapped_column(Integer, default=0, comment="Token消耗")

    # 会话上下文（用于恢复）
    context: Mapped[dict | None] = mapped_column(Text, comment="会话上下文(JSON格式)")

    # 对话摘要（长对话自动压缩）
    summary: Mapped[str | None] = mapped_column(Text, comment="对话摘要")

    # 标签
    tags: Mapped[list | None] = mapped_column(Text, comment="标签(JSON数组)")

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.conversation_id}>"


class Message(TenantBaseModel):
    """消息表"""

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_conversation", "conversation_id"),
        Index("idx_message_tenant_created", "tenant_id", "created_at"),
        {"comment": "消息表"},
    )

    # 消息标识
    message_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="消息ID"
    )
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, comment="会话ID", index=True
    )

    # 消息内容
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="角色(user/assistant/system)"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")

    # 意图识别
    intent: Mapped[str | None] = mapped_column(String(64), comment="识别到的意图")
    intent_confidence: Mapped[float | None] = mapped_column(Float, comment="意图置信度")
    entities: Mapped[dict | None] = mapped_column(Text, comment="提取的实体(JSON格式)")

    # 性能指标
    response_time: Mapped[int | None] = mapped_column(Integer, comment="响应时间(ms)")
    input_tokens: Mapped[int | None] = mapped_column(Integer, comment="输入Token数")
    output_tokens: Mapped[int | None] = mapped_column(Integer, comment="输出Token数")

    # 附件
    attachments: Mapped[list | None] = mapped_column(
        Text, comment="附件(JSON数组，包含URL等信息)"
    )

    # 关联关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message {self.message_id} ({self.role})>"
