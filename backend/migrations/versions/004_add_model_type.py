"""Add model_type column to model_configs table

Revision ID: 004_model_type
Revises: 003_api_key_prefix
Create Date: 2026-02-23

Description:
    为 model_configs 表添加 model_type 列，用于区分大语言模型(llm)、
    嵌入模型(embedding)和重排模型(rerank)。

    同时扩展 LLMProvider 支持新的提供商：moonshot、qwen、cohere、jina。
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '004_model_type'
down_revision = '003_api_key_prefix'
branch_labels = None
depends_on = None


def upgrade():
    """添加 model_type 列和索引"""
    op.execute(
        "ALTER TABLE model_configs ADD COLUMN IF NOT EXISTS model_type VARCHAR(32) NOT NULL DEFAULT 'llm'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_model_config_model_type ON model_configs (model_type)"
    )
    # api_key 字段扩展长度（支持更长的 token）
    op.execute(
        "ALTER TABLE model_configs ALTER COLUMN api_key TYPE VARCHAR(512)"
    )


def downgrade():
    """移除 model_type 列和索引"""
    op.execute("DROP INDEX IF EXISTS idx_model_config_model_type")
    op.execute("ALTER TABLE model_configs DROP COLUMN IF EXISTS model_type")
