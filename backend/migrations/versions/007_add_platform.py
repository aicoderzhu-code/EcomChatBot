"""Add platform integration tables and columns

Revision ID: 007_add_platform
Revises: 006_add_embedding_status_chunk_count
Create Date: 2026-02-24

Description:
    - 创建 platform_configs 表（电商平台对接配置）
    - 为 conversations 表添加 platform_type, platform_conversation_id 列
    - 为 users 表添加 platform_user_id 列
"""
from alembic import op


revision = '007_add_platform'
down_revision = '006_add_embedding_status_chunk_count'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 platform_configs 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS platform_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id VARCHAR(64) NOT NULL,
            platform_type VARCHAR(32) NOT NULL,
            app_key VARCHAR(128) NOT NULL,
            app_secret VARCHAR(256) NOT NULL,
            access_token VARCHAR(512),
            refresh_token VARCHAR(512),
            expires_at DATETIME,
            shop_id VARCHAR(64),
            shop_name VARCHAR(128),
            is_active INTEGER DEFAULT 0,
            auto_reply_threshold FLOAT DEFAULT 0.7,
            human_takeover_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_platform_config_tenant "
        "ON platform_configs (tenant_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_config_tenant_type "
        "ON platform_configs (tenant_id, platform_type)"
    )

    # 为 conversations 表添加平台字段
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS "
        "platform_type VARCHAR(32)"
    )
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS "
        "platform_conversation_id VARCHAR(128)"
    )

    # 为 users 表添加平台用户ID
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "platform_user_id VARCHAR(128)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS platform_configs")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS platform_type")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS platform_conversation_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS platform_user_id")
