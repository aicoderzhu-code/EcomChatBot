#!/usr/bin/env python3
"""
数据库初始化脚本
- 运行数据库迁移
- 创建超级管理员账号
- 创建测试租户和订阅
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.config import settings
from core.security import get_password_hash
from db.session import async_session_maker, engine
from models import Base
from models.admin import Admin, AdminRole
from models.tenant import Tenant, Subscription, PlanType
from datetime import datetime, timedelta


async def wait_for_db():
    """等待数据库就绪"""
    print("⏳ 等待数据库连接...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            print("✓ 数据库连接成功")
            return True
        except Exception as e:
            retry_count += 1
            print(f"  数据库未就绪 ({retry_count}/{max_retries})，等待 2 秒...")
            await asyncio.sleep(2)
    
    print("✗ 数据库连接失败")
    return False


async def create_tables():
    """创建数据库表"""
    print("📦 创建数据库表...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"✗ 数据库表创建失败: {e}")
        return False


async def create_super_admin():
    """创建超级管理员账号"""
    print("👤 创建超级管理员账号...")
    
    async with async_session_maker() as session:
        try:
            # 检查是否已存在超级管理员
            result = await session.execute(
                text("SELECT id FROM admins WHERE username = :username"),
                {"username": "admin"}
            )
            if result.first():
                print("  ⚠️  超级管理员已存在，跳过创建")
                return True
            
            # 创建超级管理员
            admin = Admin(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                full_name="超级管理员",
                role=AdminRole.SUPER_ADMIN,
                is_active=True
            )
            session.add(admin)
            await session.commit()
            
            print("✓ 超级管理员创建成功")
            print("  用户名: admin")
            print("  密码: admin123")
            print("  ⚠️  请在生产环境中立即修改密码！")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"✗ 超级管理员创建失败: {e}")
            return False


async def create_test_tenant():
    """创建测试租户"""
    print("🏢 创建测试租户...")
    
    async with async_session_maker() as session:
        try:
            # 检查是否已存在测试租户
            result = await session.execute(
                text("SELECT id FROM tenants WHERE company_name = :name"),
                {"name": "测试公司"}
            )
            if result.first():
                print("  ⚠️  测试租户已存在，跳过创建")
                return True
            
            # 创建测试租户
            tenant = Tenant(
                company_name="测试公司",
                contact_name="张三",
                contact_email="test@example.com",
                contact_phone="13800138000",
                api_key="test_sk_1234567890abcdef",  # 固定 API Key 方便测试
                is_active=True
            )
            session.add(tenant)
            await session.flush()
            
            # 创建订阅（专业版套餐）
            subscription = Subscription(
                tenant_id=tenant.id,
                plan_type=PlanType.PROFESSIONAL,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365),
                is_active=True,
                # 专业版配额
                quota_conversations=10000,
                quota_messages=100000,
                quota_tokens=10000000,
                quota_knowledge_items=10000,
                quota_storage_mb=10240,
                quota_api_calls=1000000,
                # 已使用量初始化为 0
                used_conversations=0,
                used_messages=0,
                used_tokens=0,
                used_knowledge_items=0,
                used_storage_mb=0,
                used_api_calls=0
            )
            session.add(subscription)
            await session.commit()
            
            print("✓ 测试租户创建成功")
            print(f"  租户ID: {tenant.id}")
            print(f"  API Key: {tenant.api_key}")
            print("  套餐: 专业版（有效期 1 年）")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"✗ 测试租户创建失败: {e}")
            return False


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 电商智能客服 SaaS 平台 - 数据库初始化")
    print("=" * 60)
    print()
    
    # 1. 等待数据库就绪
    if not await wait_for_db():
        sys.exit(1)
    
    print()
    
    # 2. 创建数据库表
    if not await create_tables():
        sys.exit(1)
    
    print()
    
    # 3. 创建超级管理员
    if not await create_super_admin():
        sys.exit(1)
    
    print()
    
    # 4. 创建测试租户
    if not await create_test_tenant():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ 数据库初始化完成！")
    print("=" * 60)
    print()
    print("📝 快速开始:")
    print("  1. API 文档: http://localhost:8000/docs")
    print("  2. 管理员登录:")
    print("     POST http://localhost:8000/api/admin/login")
    print("     { \"username\": \"admin\", \"password\": \"admin123\" }")
    print("  3. 测试租户 API Key: test_sk_1234567890abcdef")
    print()
    

if __name__ == "__main__":
    asyncio.run(main())
