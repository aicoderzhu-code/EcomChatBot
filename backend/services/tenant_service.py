"""
租户管理服务
"""
from datetime import datetime, timedelta
import json
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import (
    AccountLockedException,
    AuthenticationException,
    DuplicateResourceException,
    SubscriptionExpiredException,
    TenantNotFoundException,
    TenantSuspendedException,
    generate_api_key,
    generate_tenant_id,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)
from core.permissions import PLAN_CONFIGS
from models import Subscription, Tenant
from schemas.tenant import TenantCreate, TenantRegisterRequest, TenantUpdate

# 登录失败次数限制
MAX_LOGIN_ATTEMPTS = 5
# 账户锁定时间（分钟）
ACCOUNT_LOCK_MINUTES = 30


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
        api_key_prefix = api_key[:12] if len(api_key) >= 12 else api_key  # 保存前缀用于快速查找
        password_hash = hash_password(tenant_data.password)

        # 创建租户
        tenant = Tenant(
            tenant_id=tenant_id,
            company_name=tenant_data.company_name,
            contact_name=tenant_data.contact_name,
            contact_email=tenant_data.contact_email,
            contact_phone=tenant_data.contact_phone,
            password_hash=password_hash,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,  # 保存API Key前缀用于快速认证
            api_key_plain=api_key,  # 保存明文用于展示
            status="active",
            current_plan=tenant_data.initial_plan,
        )
        self.db.add(tenant)

        # 创建订阅
        plan_config = PLAN_CONFIGS.get(tenant_data.initial_plan, PLAN_CONFIGS["trial"])
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan_type=tenant_data.initial_plan,
            status="active",
            enabled_features=json.dumps([f.value for f in plan_config["features"]]),  # 转换为JSON字符串
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

        优化策略（按优先级）：
        1. 格式验证（快速拒绝无效格式）
        2. 使用 api_key_prefix 字段直接查询（O(1)，新租户）
        3. 回退到 Redis 缓存查询（旧租户）
        4. 最后回退到遍历验证（仅首次，且仅针对旧租户）
        """
        # 快速格式验证：API Key 必须以 eck_ 开头且长度足够
        if not api_key or len(api_key) < 20 or not api_key.startswith("eck_"):
            return None

        # 从 API Key 中提取前缀
        api_key_prefix = api_key[:12] if len(api_key) >= 12 else api_key

        # 方案1：直接通过 api_key_prefix 索引查询（最快，O(1)）
        stmt = select(Tenant).where(
            and_(
                Tenant.api_key_prefix == api_key_prefix,
                Tenant.status == "active"
            )
        )
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if tenant and verify_api_key(api_key, tenant.api_key_hash):
            return tenant

        # 方案2：尝试从 Redis 缓存获取（旧租户，没有 api_key_prefix）
        from db import get_cache
        try:
            cache = await get_cache()
            cache_key = f"api_key_tenant:{api_key_prefix}"
            cached_tenant_id = await cache.get(cache_key)

            if cached_tenant_id:
                stmt = select(Tenant).where(
                    and_(
                        Tenant.tenant_id == cached_tenant_id,
                        Tenant.status == "active"
                    )
                )
                result = await self.db.execute(stmt)
                tenant = result.scalar_one_or_none()

                if tenant and verify_api_key(api_key, tenant.api_key_hash):
                    return tenant
                else:
                    await cache.delete(cache_key)
        except Exception:
            pass

        # 方案3：回退到遍历验证（仅针对没有 api_key_prefix 的旧租户，首次查询）
        stmt = select(Tenant).where(
            and_(
                Tenant.status == "active",
                Tenant.api_key_prefix.is_(None)  # 只查询没有设置前缀的旧租户
            )
        ).limit(1000)
        result = await self.db.execute(stmt)
        tenants = result.scalars().all()

        for tenant in tenants:
            if verify_api_key(api_key, tenant.api_key_hash):
                # 验证成功，更新租户的 api_key_prefix 字段（永久修复）
                tenant.api_key_prefix = api_key_prefix
                await self.db.commit()

                # 同时缓存到 Redis
                try:
                    cache = await get_cache()
                    cache_key = f"api_key_tenant:{api_key_prefix}"
                    await cache.set(cache_key, tenant.tenant_id, expire=300)
                except Exception:
                    pass
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
        tenant.api_key_prefix = new_api_key[:12] if len(new_api_key) >= 12 else new_api_key  # 更新前缀
        tenant.api_key_plain = new_api_key  # 保存明文用于展示

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant, new_api_key

    async def delete_tenant(self, tenant_id: str) -> None:
        """删除租户（软删除）"""
        tenant = await self.get_tenant(tenant_id)
        tenant.status = "deleted"
        await self.db.commit()

    # ============ 批量操作方法 ============
    
    async def batch_activate_tenants(self, tenant_ids: list[str]) -> dict:
        """
        批量激活租户
        
        Returns:
            {"success": [...], "failed": [...]}
        """
        success = []
        failed = []
        
        for tenant_id in tenant_ids:
            try:
                tenant = await self.get_tenant(tenant_id)
                tenant.status = "active"
                await self.db.commit()
                success.append(tenant_id)
            except Exception as e:
                failed.append({"tenant_id": tenant_id, "error": str(e)})
        
        return {"success": success, "failed": failed}
    
    async def batch_suspend_tenants(self, tenant_ids: list[str]) -> dict:
        """
        批量暂停租户
        
        Returns:
            {"success": [...], "failed": [...]}
        """
        success = []
        failed = []
        
        for tenant_id in tenant_ids:
            try:
                tenant = await self.get_tenant(tenant_id)
                tenant.status = "suspended"
                await self.db.commit()
                success.append(tenant_id)
            except Exception as e:
                failed.append({"tenant_id": tenant_id, "error": str(e)})
        
        return {"success": success, "failed": failed}
    
    async def batch_delete_tenants(self, tenant_ids: list[str]) -> dict:
        """
        批量删除租户（软删除）
        
        Returns:
            {"success": [...], "failed": [...]}
        """
        success = []
        failed = []
        
        for tenant_id in tenant_ids:
            try:
                tenant = await self.get_tenant(tenant_id)
                tenant.status = "deleted"
                await self.db.commit()
                success.append(tenant_id)
            except Exception as e:
                failed.append({"tenant_id": tenant_id, "error": str(e)})
        
        return {"success": success, "failed": failed}
    
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

        # 检查订阅是否过期（含7天宽限期）
        if tenant.plan_expire_at and tenant.plan_expire_at + timedelta(days=7) < datetime.utcnow():
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

    # ============ 租户认证方法 ============

    async def register_tenant(
        self,
        register_data: TenantRegisterRequest,
    ) -> tuple[str, str]:
        """
        租户自助注册

        Returns:
            (tenant_id, api_key): 租户ID和API密钥（明文，仅此一次）
        """
        # 检查邮箱是否已存在
        existing = await self.get_tenant_by_email(register_data.contact_email)
        if existing:
            raise DuplicateResourceException("租户", "邮箱", register_data.contact_email)

        # 生成租户ID和API Key
        tenant_id = generate_tenant_id()
        api_key = generate_api_key()
        api_key_hash_value = hash_api_key(api_key)
        api_key_prefix = api_key[:12] if len(api_key) >= 12 else api_key  # 保存前缀用于快速查找
        password_hash_value = hash_password(register_data.password)

        # 创建试用订阅配置
        from core.permissions import SUBSCRIPTION_PLANS
        trial_config = PLAN_CONFIGS["trial"]
        trial_days = SUBSCRIPTION_PLANS["trial"]["days"]
        plan_expire_at = datetime.utcnow() + timedelta(days=trial_days)

        # 创建租户（默认试用套餐）
        tenant = Tenant(
            tenant_id=tenant_id,
            company_name=register_data.company_name,
            contact_name=register_data.contact_name,
            contact_email=register_data.contact_email,
            contact_phone=register_data.contact_phone,
            api_key_hash=api_key_hash_value,
            api_key_prefix=api_key_prefix,
            api_key_plain=api_key,  # 保存明文用于展示
            password_hash=password_hash_value,
            status="active",
            current_plan="trial",
            plan_expire_at=plan_expire_at,
            login_attempts=0,
        )
        self.db.add(tenant)
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan_type="trial",
            status="active",
            enabled_features=json.dumps([f.value if hasattr(f, 'value') else f for f in trial_config["features"]]),
            start_date=datetime.utcnow(),
            expire_at=datetime.utcnow() + timedelta(days=trial_days),
            auto_renew=False,
            is_trial=True,
        )
        self.db.add(subscription)

        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant.tenant_id, api_key

    async def authenticate_tenant(
        self,
        email: str,
        password: str,
        login_ip: str | None = None,
    ) -> Tenant:
        """
        租户登录认证

        Returns:
            Tenant: 认证成功的租户对象

        Raises:
            AuthenticationException: 认证失败
            AccountLockedException: 账户已锁定
        """
        # 获取租户
        tenant = await self.get_tenant_by_email(email)
        if not tenant:
            raise AuthenticationException("邮箱或密码错误")

        # 检查账户是否被锁定
        if tenant.locked_until and tenant.locked_until > datetime.utcnow():
            remaining_minutes = int(
                (tenant.locked_until - datetime.utcnow()).total_seconds() / 60
            )
            raise AccountLockedException(
                f"账户已锁定，请在 {remaining_minutes} 分钟后重试"
            )

        # 检查密码是否设置
        if not tenant.password_hash:
            raise AuthenticationException("该账户未设置密码，请联系管理员")

        # 验证密码
        if not verify_password(password, tenant.password_hash):
            await self.increment_login_attempts(tenant.tenant_id)
            raise AuthenticationException("邮箱或密码错误")

        # 检查租户状态
        if tenant.status == "suspended":
            raise TenantSuspendedException("租户服务已暂停，请联系管理员")
        if tenant.status == "deleted":
            raise AuthenticationException("账户不存在")

        # 认证成功，重置登录尝试次数
        await self.reset_login_attempts(tenant.tenant_id)

        # 更新最后登录信息
        tenant.last_login_at = datetime.utcnow()
        if login_ip:
            tenant.last_login_ip = login_ip
        await self.db.commit()
        await self.db.refresh(tenant)

        return tenant

    async def store_refresh_token(self, tenant_id: str, refresh_token: str) -> None:
        """存储刷新 Token 哈希"""
        tenant = await self.get_tenant(tenant_id)
        tenant.refresh_token_hash = hash_api_key(refresh_token)
        await self.db.commit()

    async def verify_refresh_token(self, tenant_id: str, refresh_token: str) -> bool:
        """验证刷新 Token"""
        tenant = await self.get_tenant(tenant_id)
        if not tenant.refresh_token_hash:
            return False
        return verify_api_key(refresh_token, tenant.refresh_token_hash)

    async def invalidate_refresh_token(self, tenant_id: str) -> None:
        """使刷新 Token 失效"""
        tenant = await self.get_tenant(tenant_id)
        tenant.refresh_token_hash = None
        await self.db.commit()

    async def increment_login_attempts(self, tenant_id: str) -> None:
        """增加登录失败次数"""
        tenant = await self.get_tenant(tenant_id)
        tenant.login_attempts += 1

        # 超过最大尝试次数，锁定账户
        if tenant.login_attempts >= MAX_LOGIN_ATTEMPTS:
            tenant.locked_until = datetime.utcnow() + timedelta(
                minutes=ACCOUNT_LOCK_MINUTES
            )

        await self.db.commit()

    async def reset_login_attempts(self, tenant_id: str) -> None:
        """重置登录尝试次数"""
        tenant = await self.get_tenant(tenant_id)
        tenant.login_attempts = 0
        tenant.locked_until = None
        await self.db.commit()

    async def change_password(
        self,
        tenant_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        """修改密码"""
        tenant = await self.get_tenant(tenant_id)

        # 验证当前密码
        if not tenant.password_hash or not verify_password(current_password, tenant.password_hash):
            raise AuthenticationException("当前密码错误")

        # 更新密码
        tenant.password_hash = hash_password(new_password)
        # 清除 refresh_token，要求其他设备重新登录
        tenant.refresh_token_hash = None
        await self.db.commit()

    async def update_tenant_config(
        self, tenant_id: str, config_updates: dict
    ) -> Tenant:
        """
        更新租户自定义配置
        
        Args:
            tenant_id: 租户ID
            config_updates: 配置更新字典
            
        Returns:
            更新后的租户对象
        """
        tenant = await self.get_tenant(tenant_id)
        
        # 获取现有配置
        existing_config = tenant.config or {}
        
        # 合并配置（支持部分更新）
        existing_config.update(config_updates)
        
        # 更新租户配置
        tenant.config = existing_config
        
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return tenant
