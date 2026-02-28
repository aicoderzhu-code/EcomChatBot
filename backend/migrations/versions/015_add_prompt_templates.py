"""Add prompt_templates table

Revision ID: 015_add_prompt_templates
Revises: 014_add_generation_model_types
Create Date: 2026-02-28

Description:
    创建 prompt_templates 表（提示词模板）。
"""

from alembic import op

revision = "015_add_prompt_templates"
down_revision = "014_add_generation_model_types"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            name VARCHAR(128) NOT NULL,
            template_type VARCHAR(32) NOT NULL,
            content TEXT NOT NULL,
            variables TEXT,
            is_default INTEGER NOT NULL DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_prompt_template_tenant ON prompt_templates (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_prompt_template_type ON prompt_templates (template_type)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS prompt_templates")
