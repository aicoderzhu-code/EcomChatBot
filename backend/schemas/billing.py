"""
账单和欠费相关的Schema定义
"""
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.base import BaseSchema


# ==================== 欠费租户信息 ====================
class OverdueTenantInfo(BaseModel):
    """欠费租户信息"""

    tenant_id: str = Field(..., description="租户ID")
    company_name: str = Field(..., description="公司名称")
    contact_name: str | None = Field(None, description="联系人")
    email: str = Field(..., description="邮箱")
    phone: str | None = Field(None, description="手机")
    total_overdue: float = Field(..., description="总欠费金额")
    overdue_bills_count: int = Field(..., description="欠费账单数量")
    days_overdue: int = Field(..., description="逾期天数")
    oldest_due_date: datetime | None = Field(None, description="最早到期日期")
    degradation_level: str | None = Field(None, description="降级等级")


class OverdueTenantListResponse(BaseModel):
    """欠费租户列表响应"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    items: list[OverdueTenantInfo] = Field(default_factory=list, description="租户列表")


# ==================== 催款提醒 ====================
class SendReminderRequest(BaseSchema):
    """发送催款提醒请求"""

    custom_message: str | None = Field(None, max_length=500, description="自定义提醒消息")
    send_email: bool = Field(True, description="是否发送邮件")
    send_sms: bool = Field(False, description="是否发送短信")


class SendReminderResponse(BaseModel):
    """发送催款提醒响应"""

    message: str = Field(..., description="响应消息")
    email_sent: bool = Field(False, description="邮件是否发送成功")
    sms_sent: bool = Field(False, description="短信是否发送成功")


# ==================== 账单审核 ====================
class PendingBillInfo(BaseModel):
    """待审核账单信息"""

    bill_id: str = Field(..., description="账单ID")
    tenant_id: str = Field(..., description="租户ID")
    company_name: str = Field(..., description="公司名称")
    amount: float = Field(..., description="账单金额")
    billing_period_start: datetime = Field(..., description="账单周期开始")
    billing_period_end: datetime = Field(..., description="账单周期结束")
    due_date: datetime = Field(..., description="到期日期")
    created_at: datetime = Field(..., description="创建时间")


class ApproveBillRequest(BaseSchema):
    """审核通过请求"""

    note: str | None = Field(None, max_length=500, description="审核备注")


class RejectBillRequest(BaseSchema):
    """审核拒绝请求"""

    reason: str = Field(..., min_length=1, max_length=500, description="拒绝原因")
