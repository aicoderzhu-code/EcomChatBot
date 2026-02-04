"""
数据库初始化脚本
- 创建所有表
- 创建默认超级管理员
- 创建默认套餐配置
"""
import asyncio
import sys
from sqlalchemy import text

from db.session import engine, AsyncSessionLocal
from models import Base
from models.admin import Admin
from core.security import get_password_hash
from core.permissions import AdminRole


async def init_database():
    """初始化数据库"""
    print("🚀 开始初始化数据库...")
    
    # 1. 创建所有表
    print("📦 创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建完成")
    
    # 2. 创建默认超级管理员
    print("👤 创建默认超级管理员...")
    async with AsyncSessionLocal() as session:
        # 检查是否已存在管理员
        result = await session.execute(
            text("SELECT COUNT(*) FROM admins")
        )
        count = result.scalar()
        
        if count == 0:
            # 创建超级管理员
            super_admin = Admin(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123456"),
                full_name="超级管理员",
                role=AdminRole.SUPER_ADMIN,
                is_active=True
            )
            session.add(super_admin)
            await session.commit()
            print("✅ 默认超级管理员创建成功")
            print("   用户名: admin")
            print("   密码: admin123456")
            print("   ⚠️  请在生产环境中立即修改默认密码！")
        else:
            print("ℹ️  管理员已存在，跳过创建")
    
    print("🎉 数据库初始化完成！")


async def check_database_connection():
    """检查数据库连接"""
    print("🔍 检查数据库连接...")
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"⏳ 等待数据库启动... ({i + 1}/{max_retries})")
                await asyncio.sleep(retry_interval)
            else:
                print(f"❌ 数据库连接失败: {e}")
                return False
    return False


async def main():
    """主函数"""
    try:
        # 检查数据库连接
        if not await check_database_connection():
            sys.exit(1)
        
        # 初始化数据库
        await init_database()
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
