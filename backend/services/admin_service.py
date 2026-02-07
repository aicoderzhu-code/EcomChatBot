"""
管理员服务
"""
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import (
    AccountLockedException,
    AdminNotFoundException,
    AdminRole,
    DuplicateResourceException,
    generate_admin_id,
    hash_password,
    verify_password,
)
from models import Admin


class AdminService:
    """管理员服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_admin(
        self,
        username: str,
        password: str,
        email: str,
        role: AdminRole,
        phone: str | None = None,
        created_by: str | None = None,
    ) -> Admin:
        """创建管理员"""
        # 检查用户名和邮箱是否已存在
        existing_username = await self.get_admin_by_username(username)
        if existing_username:
            raise DuplicateResourceException("管理员", "用户名", username)

        existing_email = await self.get_admin_by_email(email)
        if existing_email:
            raise DuplicateResourceException("管理员", "邮箱", email)

        # 创建管理员
        admin_id = generate_admin_id()
        password_hash = hash_password(password)

        admin = Admin(
            admin_id=admin_id,
            username=username,
            password_hash=password_hash,
            email=email,
            phone=phone,
            role=role.value,
            status="active",
            created_by=created_by,
        )

        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)

        return admin

    async def get_admin(self, admin_id: str) -> Admin:
        """获取管理员"""
        stmt = select(Admin).where(Admin.admin_id == admin_id)
        result = await self.db.execute(stmt)
        admin = result.scalar_one_or_none()

        if not admin:
            raise AdminNotFoundException(admin_id)

        return admin

    async def get_admin_by_username(self, username: str) -> Admin | None:
        """根据用户名获取管理员"""
        stmt = select(Admin).where(Admin.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admin_by_email(self, email: str) -> Admin | None:
        """根据邮箱获取管理员"""
        stmt = select(Admin).where(Admin.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def authenticate_admin(
        self,
        username: str,
        password: str,
        ip_address: str | None = None,
    ) -> Admin:
        """
        管理员登录认证
        """
        admin = await self.get_admin_by_username(username)
        if not admin:
            return None

        # 检查账号是否锁定
        if admin.locked_until and admin.locked_until > datetime.utcnow():
            raise AccountLockedException(
                f"账号已被锁定，解锁时间: {admin.locked_until.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # 验证密码
        if not verify_password(password, admin.password_hash):
            # 登录失败次数 +1
            await self.increment_login_attempts(admin.admin_id)
            return None

        # 重置登录失败次数
        await self.reset_login_attempts(admin.admin_id)

        # 更新最后登录信息
        admin.last_login_at = datetime.utcnow()
        admin.last_login_ip = ip_address
        await self.db.commit()

        return admin

    async def increment_login_attempts(self, admin_id: str) -> None:
        """增加登录失败次数"""
        admin = await self.get_admin(admin_id)
        admin.login_attempts += 1

        # 如果失败次数 >= 5，锁定账号30分钟
        if admin.login_attempts >= 5:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=30)

        await self.db.commit()

    async def reset_login_attempts(self, admin_id: str) -> None:
        """重置登录失败次数"""
        admin = await self.get_admin(admin_id)
        admin.login_attempts = 0
        admin.locked_until = None
        await self.db.commit()

    async def update_admin_status(self, admin_id: str, status: str) -> Admin:
        """更新管理员状态"""
        admin = await self.get_admin(admin_id)
        admin.status = status
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def change_password(
        self,
        admin_id: str,
        old_password: str,
        new_password: str,
    ) -> None:
        """修改密码"""
        admin = await self.get_admin(admin_id)

        # 验证旧密码
        if not verify_password(old_password, admin.password_hash):
            raise ValueError("原密码错误")

        # 更新密码
        admin.password_hash = hash_password(new_password)
        await self.db.commit()

    async def reset_password(self, admin_id: str, new_password: str) -> None:
        """重置密码（管理员操作）"""
        admin = await self.get_admin(admin_id)
        admin.password_hash = hash_password(new_password)
        await self.db.commit()

    async def list_admins(
        self,
        page: int = 1,
        size: int = 20,
        role: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Admin], int]:
        """
        获取管理员列表

        Args:
            page: 页码
            size: 每页数量
            role: 角色过滤
            status: 状态过滤
            keyword: 搜索关键词（用户名/邮箱/手机）

        Returns:
            (管理员列表, 总数)
        """
        stmt = select(Admin).where(Admin.status != "deleted")
        count_stmt = select(func.count(Admin.id)).where(Admin.status != "deleted")

        # 角色过滤
        if role:
            stmt = stmt.where(Admin.role == role)
            count_stmt = count_stmt.where(Admin.role == role)

        # 状态过滤
        if status:
            stmt = stmt.where(Admin.status == status)
            count_stmt = count_stmt.where(Admin.status == status)

        # 关键词搜索
        if keyword:
            search_filter = or_(
                Admin.username.ilike(f"%{keyword}%"),
                Admin.email.ilike(f"%{keyword}%"),
                Admin.phone.ilike(f"%{keyword}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # 获取总数
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        stmt = stmt.order_by(Admin.created_at.desc())
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self.db.execute(stmt)
        admins = result.scalars().all()

        return list(admins), total

    async def update_admin(
        self,
        admin_id: str,
        email: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        status: str | None = None,
        updated_by: str | None = None,
    ) -> Admin:
        """
        更新管理员信息

        Args:
            admin_id: 管理员ID
            email: 新邮箱
            phone: 新手机号
            role: 新角色
            status: 新状态
            updated_by: 更新人

        Returns:
            更新后的管理员
        """
        admin = await self.get_admin(admin_id)

        # 检查邮箱唯一性
        if email and email != admin.email:
            existing = await self.get_admin_by_email(email)
            if existing:
                raise DuplicateResourceException("管理员", "邮箱", email)
            admin.email = email

        if phone is not None:
            admin.phone = phone

        if role:
            admin.role = role

        if status:
            admin.status = status

        admin.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(admin)

        return admin

    async def delete_admin(self, admin_id: str, deleted_by: str) -> None:
        """
        删除管理员（软删除）

        Args:
            admin_id: 管理员ID
            deleted_by: 删除人
        """
        admin = await self.get_admin(admin_id)

        # 不能删除自己
        if admin_id == deleted_by:
            raise ValueError("不能删除自己")

        admin.status = "deleted"
        admin.updated_at = datetime.utcnow()
        await self.db.commit()
