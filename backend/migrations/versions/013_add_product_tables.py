"""Add product sync tables

Revision ID: 013_add_product_tables
Revises: 012_remove_quota_system
Create Date: 2026-02-28

Description:
    - 创建 products 表（商品数据）
    - 创建 platform_sync_tasks 表（同步任务）
    - 创建 product_sync_schedules 表（同步调度配置）
"""

from alembic import op

revision = "013_add_product_tables"
down_revision = "012_remove_quota_system"
branch_labels = None
depends_on = None


def upgrade():
    # 创建 products 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            platform_config_id INTEGER NOT NULL,
            platform_product_id VARCHAR(128) NOT NULL,
            title VARCHAR(512) NOT NULL,
            description TEXT,
            price NUMERIC(10, 2) NOT NULL,
            original_price NUMERIC(10, 2),
            currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
            category VARCHAR(128),
            images TEXT,
            videos TEXT,
            attributes TEXT,
            sales_count INTEGER DEFAULT 0,
            stock INTEGER DEFAULT 0,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            platform_data TEXT,
            knowledge_base_id INTEGER,
            last_synced_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_product_tenant ON products (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_platform ON products (platform_config_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_platform_id ON products (platform_product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_status ON products (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_category ON products (category)")

    # 创建 platform_sync_tasks 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS platform_sync_tasks (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            platform_config_id INTEGER NOT NULL,
            sync_target VARCHAR(32) NOT NULL,
            sync_type VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            total_count INTEGER DEFAULT 0,
            synced_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_sync_task_tenant ON platform_sync_tasks (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sync_task_status ON platform_sync_tasks (status)")

    # 创建 product_sync_schedules 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS product_sync_schedules (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            platform_config_id INTEGER NOT NULL,
            interval_minutes INTEGER NOT NULL DEFAULT 60,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_run_at TIMESTAMP,
            next_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_sync_schedule_tenant ON product_sync_schedules (tenant_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS product_sync_schedules")
    op.execute("DROP TABLE IF EXISTS platform_sync_tasks")
    op.execute("DROP TABLE IF EXISTS products")
