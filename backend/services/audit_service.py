"""
审计日志服务
"""
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AdminOperationLog


class AuditService:
    """审计日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_operation(
        self,
        admin_id: str,
        operation_type: str,
        resource_type: str,
        resource_id: str,
        operation_details: dict | None = None,
        before_value: dict | None = None,
        after_value: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> AdminOperationLog:
        """
        记录操作日志
        """
        log = AdminOperationLog(
            admin_id=admin_id,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            operation_details=operation_details,
            before_value=before_value,
            after_value=after_value,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return log

    async def get_operation_logs(
        self,
        admin_id: str | None = None,
        resource_type: str | None = None,
        operation_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[AdminOperationLog], int]:
        """查询操作日志"""
        conditions = []

        if admin_id:
            conditions.append(AdminOperationLog.admin_id == admin_id)
        if resource_type:
            conditions.append(AdminOperationLog.resource_type == resource_type)
        if operation_type:
            conditions.append(AdminOperationLog.operation_type == operation_type)
        if start_date:
            conditions.append(AdminOperationLog.created_at >= start_date)
        if end_date:
            conditions.append(AdminOperationLog.created_at <= end_date)

        # 查询总数
        from sqlalchemy import func

        count_stmt = select(func.count(AdminOperationLog.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        # 分页查询
        stmt = select(AdminOperationLog).order_by(AdminOperationLog.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total or 0

    async def log_tenant_create(
        self,
        admin_id: str,
        tenant_id: str,
        tenant_data: dict,
        ip_address: str | None = None,
    ) -> AdminOperationLog:
        """记录创建租户"""
        return await self.log_operation(
            admin_id=admin_id,
            operation_type="create",
            resource_type="tenant",
            resource_id=tenant_id,
            operation_details=tenant_data,
            after_value=tenant_data,
            ip_address=ip_address,
        )

    async def log_tenant_update(
        self,
        admin_id: str,
        tenant_id: str,
        before: dict,
        after: dict,
        ip_address: str | None = None,
    ) -> AdminOperationLog:
        """记录更新租户"""
        return await self.log_operation(
            admin_id=admin_id,
            operation_type="update",
            resource_type="tenant",
            resource_id=tenant_id,
            before_value=before,
            after_value=after,
            ip_address=ip_address,
        )

    async def log_quota_adjustment(
        self,
        admin_id: str,
        tenant_id: str,
        quota_type: str,
        amount: int,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AdminOperationLog:
        """记录配额调整"""
        return await self.log_operation(
            admin_id=admin_id,
            operation_type="adjust_quota",
            resource_type="quota",
            resource_id=tenant_id,
            operation_details={
                "quota_type": quota_type,
                "amount": amount,
                "reason": reason,
            },
            ip_address=ip_address,
        )

    async def log_bill_adjustment(
        self,
        admin_id: str,
        bill_id: str,
        amount: float,
        reason: str,
        ip_address: str | None = None,
    ) -> AdminOperationLog:
        """记录账单调整"""
        return await self.log_operation(
            admin_id=admin_id,
            operation_type="adjust_bill",
            resource_type="bill",
            resource_id=bill_id,
            operation_details={
                "adjustment_amount": amount,
                "reason": reason,
            },
            ip_address=ip_address,
        )

    async def log_plan_change(
        self,
        admin_id: str,
        tenant_id: str,
        old_plan: str,
        new_plan: str,
        ip_address: str | None = None,
    ) -> AdminOperationLog:
        """记录套餐变更"""
        return await self.log_operation(
            admin_id=admin_id,
            operation_type="change_plan",
            resource_type="subscription",
            resource_id=tenant_id,
            operation_details={
                "old_plan": old_plan,
                "new_plan": new_plan,
            },
            before_value={"plan": old_plan},
            after_value={"plan": new_plan},
            ip_address=ip_address,
        )
