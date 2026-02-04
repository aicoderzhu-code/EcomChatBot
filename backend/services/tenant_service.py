"""
租户管理服务
"""
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import (
    DuplicateResourceException,
    SubscriptionExpiredException,
    TenantNotFoundException,
    TenantSuspendedException,
    generate_api_key,
    generate_tenant_id,
    hash_api_key,
    verify_api_key,
)
from core.permissions import PLAN_CONFIGS
from models import Subscription, Tenant
from schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    """租户管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(
        self,
        tenant_data: TenantCreate,
        created_by: str | None = None,
    ) -> tuple[Tenant, str]:
        """
        创建租户（代客开户）
        
        Returns:
            (Tenant, api_key): 租户对象和API密钥（明文，仅此一次）
        """
        # 检查邮箱是否已存在
        existing = await self.get_tenant_by_email(tenant_data.contact_email)
        if existing:
            raise DuplicateResourceException("租户", "邮箱", tenant_data.contact_email)

        # 生成租户ID和API Key
        tenant_id = generate_tenant_id()
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)

        # 创建租户
        tenant = Tenant(
            tenant_id=tenant_id,
            company_name=tenant_data.company_name,
            contact_name=tenant_data.contact_name,
            contact_email=tenant_data.contact_email,
            contact_phone=tenant_data.contact_phone,
            api_key_hash=api_key_hash,
            status="active",
            current_plan=tenant_data.initial_plan,
        )
        self.db.add(tenant)

        # 创建订阅
        plan_config = PLAN_CONFIGS.get(tenant_data.initial_plan, PLAN_CONFIGS["free"])
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_type=tenant_data.initial_plan,
            status="active",
            enabled_features=plan_config["features"],
            conversation_quota=plan_config["conversation_quota"],
            concurrent_quota=plan_config["concurrent_quota"],
            storage_quota=plan_config["storage_quota"],
            api_quota=plan_config["api_quota"],
            start_date=datetime.utcnow(),
            expire_at=datetime.utcnow() + timedelta(days=365),
            auto_renew=False,
            is_trial=tenant_data.initial_plan == "free",
        )
        self.db.add(subscription)

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant, api_key

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """获取租户"""
        stmt = select(Tenant).where(Tenant.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise TenantNotFoundException(tenant_id)

        return tenant

    async def get_tenant_by_email(self, email: str) -> Tenant | None:
        """根据邮箱获取租户"""
        stmt = select(Tenant).where(Tenant.contact_email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_by_api_key(self, api_key: str) -> Tenant | None:
        """
        根据 API Key 获取租户（用于认证）
        
        注意：需要验证API Key哈希值
        """
        # 获取所有激活的租户
        stmt = select(Tenant).where(Tenant.status == "active")
        result = await self.db.execute(stmt)
        tenants = result.scalars().all()

        # 验证API Key
        for tenant in tenants:
            if verify_api_key(api_key, tenant.api_key_hash):
                return tenant

        return None

    async def list_tenants(
        self,
        page: int = 1,
        size: int = 20,
        status: str | None = None,
        plan: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Tenant], int]:
        """
        查询租户列表（分页、搜索、筛选）
        """
        # 构建查询条件
        conditions = []
        if status:
            conditions.append(Tenant.status == status)
        if plan:
            conditions.append(Tenant.current_plan == plan)
        if keyword:
            conditions.append(
                or_(
                    Tenant.company_name.ilike(f"%{keyword}%"),
                    Tenant.contact_email.ilike(f"%{keyword}%"),
                    Tenant.tenant_id.ilike(f"%{keyword}%"),
                )
            )

        # 查询总数
        count_stmt = select(func.count(Tenant.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await self.db.scalar(count_stmt)

        # 分页查询
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self.db.execute(stmt)
        tenants = result.scalars().all()

        return list(tenants), total or 0

    async def update_tenant(self, tenant_id: str, tenant_data: TenantUpdate) -> Tenant:
        """更新租户信息"""
        tenant = await self.get_tenant(tenant_id)

        # 更新字段
        update_data = tenant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant

    async def update_tenant_status(
        self,
        tenant_id: str,
        status: str,
        reason: str | None = None,
    ) -> Tenant:
        """更新租户状态"""
        tenant = await self.get_tenant(tenant_id)
        tenant.status = status

        if status == "suspended":
            # 暂停服务：可以添加额外逻辑，如关闭所有会话
            pass

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant

    async def reset_api_key(self, tenant_id: str) -> tuple[Tenant, str]:
        """
        重置 API Key
        
        Returns:
            (Tenant, api_key): 租户对象和新的API密钥（明文）
        """
        tenant = await self.get_tenant(tenant_id)

        # 生成新的API Key
        new_api_key = generate_api_key()
        tenant.api_key_hash = hash_api_key(new_api_key)

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant, new_api_key

    async def delete_tenant(self, tenant_id: str) -> None:
        """删除租户（软删除）"""
        tenant = await self.get_tenant(tenant_id)
        tenant.status = "deleted"
        await self.db.commit()

    async def check_tenant_access(self, tenant_id: str) -> None:
        """
        检查租户访问权限
        
        Raises:
            TenantNotFoundException: 租户不存在
            TenantSuspendedException: 租户已暂停
            SubscriptionExpiredException: 订阅已过期
        """
        tenant = await self.get_tenant(tenant_id)

        # 检查状态
        if tenant.status == "suspended":
            raise TenantSuspendedException("租户服务已暂停，请联系管理员")
        if tenant.status == "deleted":
            raise TenantNotFoundException(tenant_id)

        # 检查订阅是否过期
        if tenant.plan_expire_at and tenant.plan_expire_at < datetime.utcnow():
            raise SubscriptionExpiredException("订阅已过期，请续费")

    async def update_last_active(self, tenant_id: str) -> None:
        """更新最后活跃时间"""
        tenant = await self.get_tenant(tenant_id)
        tenant.last_active_at = datetime.utcnow()
        await self.db.commit()

    async def increment_conversation_count(self, tenant_id: str) -> None:
        """增加对话计数"""
        tenant = await self.get_tenant(tenant_id)
        tenant.total_conversations += 1
        await self.db.commit()

    async def increment_message_count(self, tenant_id: str, count: int = 1) -> None:
        """增加消息计数"""
        tenant = await self.get_tenant(tenant_id)
        tenant.total_messages += count
        await self.db.commit()
