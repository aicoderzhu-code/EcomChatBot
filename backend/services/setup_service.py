"""
系统初始化服务
"""
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import AdminRole, DuplicateResourceException, generate_admin_id, hash_password
from models import Admin
from schemas.setup import InitialAdminCreate, SetupStatus

logger = logging.getLogger(__name__)


class SetupService:
    """系统初始化服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_initialization_status(self) -> SetupStatus:
        """
        检查系统初始化状态

        Returns:
            SetupStatus: 包含 initialized 和 admin_count
        """
        stmt = select(func.count(Admin.id)).where(Admin.status != "deleted")
        result = await self.db.execute(stmt)
        admin_count = result.scalar() or 0

        return SetupStatus(
            initialized=admin_count > 0,
            admin_count=admin_count
        )

    async def create_initial_admin(self, data: InitialAdminCreate) -> Admin:
        """
        创建初始超级管理员

        Args:
            data: 初始管理员创建数据

        Returns:
            Admin: 创建的管理员对象

        Raises:
            ValueError: 系统已初始化或验证失败
            DuplicateResourceException: 用户名或邮箱已存在
        """
        # 检查是否已初始化
        status = await self.check_initialization_status()
        if status.initialized:
            raise ValueError("系统已初始化，无法再次创建初始管理员")

        # 验证密码强度
        if not self.validate_password_strength(data.password):
            raise ValueError("密码不符合强度要求")

        # 检查用户名是否已存在
        stmt = select(Admin).where(Admin.username == data.username)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise DuplicateResourceException("管理员", "用户名", data.username)

        # 检查邮箱是否已存在
        stmt = select(Admin).where(Admin.email == data.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise DuplicateResourceException("管理员", "邮箱", data.email)

        # 创建超级管理员
        admin = Admin(
            admin_id=generate_admin_id(),
            username=data.username,
            password_hash=hash_password(data.password),
            email=data.email,
            phone=data.phone,
            role=AdminRole.SUPER_ADMIN.value,
            status="active",
            created_by="system_setup",
        )

        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)

        logger.info(f"初始超级管理员创建成功: {admin.username} ({admin.admin_id})")

        return admin

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        验证密码强度

        要求:
        - 至少8个字符
        - 包含至少一个小写字母
        - 包含至少一个大写字母
        - 包含至少一个数字

        Args:
            password: 密码

        Returns:
            bool: 是否符合强度要求
        """
        if len(password) < 8:
            return False

        if not re.search(r"[a-z]", password):
            return False

        if not re.search(r"[A-Z]", password):
            return False

        if not re.search(r"\d", password):
            return False

        return True

    @staticmethod
    def get_password_strength(password: str) -> str:
        """
        获取密码强度等级

        Args:
            password: 密码

        Returns:
            str: 强度等级 (weak/medium/strong)
        """
        score = 0

        # 长度评分
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1

        # 字符类型评分
        if re.search(r"[a-z]", password):
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1

        if score <= 2:
            return "weak"
        elif score <= 4:
            return "medium"
        else:
            return "strong"
