#!/usr/bin/env python3
"""
管理员账号初始化脚本

用于测试前初始化管理员账号
"""
import asyncio
import sys
import uuid

# 确保容器内路径正确
sys.path.insert(0, '/app')

from db.session import AsyncSessionLocal
from models.admin import Admin
from core.security import hash_password
from sqlalchemy import select


async def init_admin():
    """初始化管理员账号"""
    async with AsyncSessionLocal() as db:
        # 查询管理员账号
        result = await db.execute(
            select(Admin).where(Admin.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if admin:
            # 重置密码并解锁
            admin.password_hash = hash_password("admin123")
            admin.login_attempts = 0
            admin.locked_until = None
            admin.status = "active"
            print("✅ 管理员账号已重置并解锁")
        else:
            # 创建管理员账号
            admin = Admin(
                admin_id=f"admin_{uuid.uuid4().hex[:8]}",
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                role="super_admin",
                status="active",
                login_attempts=0,
                locked_until=None
            )
            db.add(admin)
            print("✅ 管理员账号已创建")
        
        await db.commit()
        print(f"   用户名: admin")
        print(f"   密码: admin123")
        print(f"   角色: super_admin")


if __name__ == "__main__":
    try:
        asyncio.run(init_admin())
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
