#!/usr/bin/env python3
"""
数据库重置脚本

用于清空数据库所有数据（保留表结构），用于开发/测试环境重置。

使用方式:
    python reset_db.py

警告: 此脚本会删除所有数据，仅在确认需要时使用！
"""
import asyncio
import sys
from typing import NoReturn

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到 Python 路径
sys.path.insert(0, ".")

from db.session import AsyncSessionLocal, engine


# 按依赖关系排序的表清单（从被依赖最少到最多）
# 先删除有外键依赖的表，最后删除基础表
TABLES_IN_ORDER = [
    # 日志和审计表（无外键依赖）
    "admin_operation_logs",
    "audit_logs",
    "webhook_logs",
    "knowledge_usage_logs",

    # 通知表
    "in_app_notifications",
    "notification_preferences",

    # 配额调整日志
    "quota_adjustment_logs",

    # 发票相关
    "invoices",
    "invoice_titles",

    # 支付相关
    "payment_transactions",
    "payment_orders",
    "payment_channel_configs",

    # 对话相关
    "messages",
    "conversations",
    "users",

    # 知识库
    "knowledge_bases",

    # 模型配置
    "model_configs",

    # Webhook配置
    "webhook_configs",

    # 敏感词
    "sensitive_words",

    # 租户相关
    "usage_records",
    "bills",
    "subscriptions",
    "tenants",

    # 权限模板
    "permission_templates",

    # 管理员表（最后删除）
    "platform_admins",
]


async def reset_database() -> None:
    """重置数据库（清空所有表数据）"""
    async with AsyncSessionLocal() as session:
        session: AsyncSession

        print("=" * 50)
        print("开始重置数据库...")
        print("=" * 50)

        # 禁用外键检查（PostgreSQL）
        await session.execute(text("SET session_replication_role = 'replica';"))

        for table_name in TABLES_IN_ORDER:
            try:
                # 检查表是否存在
                result = await session.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT FROM information_schema.tables "
                        "WHERE table_name = :table_name"
                        ")"
                    ),
                    {"table_name": table_name}
                )
                exists = result.scalar()

                if not exists:
                    print(f"  跳过 {table_name} (表不存在)")
                    continue

                # 清空表数据并重置序列
                await session.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE;'))
                print(f"  ✓ 已清空 {table_name}")

            except Exception as e:
                print(f"  ✗ 清空 {table_name} 失败: {e}")

        # 恢复外键检查
        await session.execute(text("SET session_replication_role = 'origin';"))

        await session.commit()

        print("=" * 50)
        print("数据库重置完成！")
        print("=" * 50)


def confirm_reset() -> bool:
    """确认重置操作"""
    print("\n" + "!" * 50)
    print("警告: 此操作将删除数据库中的所有数据！")
    print("!" * 50 + "\n")

    response = input("确认要重置数据库吗? (输入 'yes' 确认): ")
    return response.strip().lower() == "yes"


def main() -> NoReturn:
    """主函数"""
    # 检查命令行参数
    force = "--force" in sys.argv or "-f" in sys.argv

    if not force:
        if not confirm_reset():
            print("操作已取消")
            sys.exit(0)

    try:
        asyncio.run(reset_database())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n操作已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n重置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
