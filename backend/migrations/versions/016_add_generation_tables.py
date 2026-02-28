"""Add generation_tasks and generated_assets tables

Revision ID: 016_add_generation_tables
Revises: 015_add_prompt_templates
Create Date: 2026-02-28

Description:
    - 创建 generation_tasks 表（内容生成任务）
    - 创建 generated_assets 表（生成资产）
"""

from alembic import op

revision = "016_add_generation_tables"
down_revision = "015_add_prompt_templates"
branch_labels = None
depends_on = None


def upgrade():
    # 创建 generation_tasks 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS generation_tasks (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            product_id INTEGER,
            task_type VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            prompt TEXT NOT NULL,
            model_config_id INTEGER,
            template_id INTEGER,
            params TEXT,
            result_count INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_task_tenant ON generation_tasks (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_task_product ON generation_tasks (product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_task_status ON generation_tasks (status)")

    # 创建 generated_assets 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS generated_assets (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            task_id INTEGER NOT NULL,
            product_id INTEGER,
            asset_type VARCHAR(32) NOT NULL,
            file_url VARCHAR(1024),
            content TEXT,
            thumbnail_url VARCHAR(1024),
            metadata TEXT,
            platform_url VARCHAR(1024),
            is_selected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_asset_tenant ON generated_assets (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_asset_task ON generated_assets (task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gen_asset_product ON generated_assets (product_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS generated_assets")
    op.execute("DROP TABLE IF EXISTS generation_tasks")
