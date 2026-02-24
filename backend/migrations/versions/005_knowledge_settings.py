"""Add knowledge_settings table

Revision ID: 005_knowledge_settings
Revises: 004_model_type
Create Date: 2026-02-23

Description:
    新增 knowledge_settings 表，存储每个租户的知识库配置：
    - embedding_model_id: 选用的嵌入模型（关联 model_configs.id）
    - rerank_model_id: 选用的重排模型（关联 model_configs.id）
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '005_knowledge_settings'
down_revision = '004_model_type'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_settings (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) UNIQUE NOT NULL,
            embedding_model_id INTEGER,
            rerank_model_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ks_tenant ON knowledge_settings (tenant_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_ks_tenant")
    op.execute("DROP TABLE IF EXISTS knowledge_settings")
