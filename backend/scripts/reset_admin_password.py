"""
重置管理员密码为测试密码 admin123
用于测试环境的管理员账号准备
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session
from app.models.admin import Admin
from app.core.security import get_password_hash


async def reset_admin_password():
    """重置管理员密码并解锁账号"""
    try:
        async with async_session() as db:
            # 查询管理员账号
            result = await db.execute(
                select(Admin).where(Admin.username == "admin")
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("❌ 管理员账号不存在，创建新账号...")
                admin = Admin(
                    username="admin",
                    email="admin@example.com",
                    password_hash=get_password_hash("admin123"),
                    is_super_admin=True,
                    is_active=True,
                    failed_login_attempts=0,
                    locked_until=None
                )
                db.add(admin)
                print("✅ 已创建管理员账号")
            else:
                print(f"✓ 找到管理员账号: {admin.username}")
                # 重置密码并解锁
                admin.password_hash = get_password_hash("admin123")
                admin.failed_login_attempts = 0
                admin.locked_until = None
                admin.is_active = True
                print("✅ 已重置密码并解锁账号")
            
            await db.commit()
            
            print("\n" + "="*50)
            print("管理员账号信息:")
            print(f"  用户名: admin")
            print(f"  密码: admin123")
            print(f"  邮箱: {admin.email if hasattr(admin, 'email') else 'N/A'}")
            print(f"  状态: {'激活' if admin.is_active else '未激活'}")
            print("="*50)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 开始重置管理员账号...")
    asyncio.run(reset_admin_password())
    print("✅ 完成！")
