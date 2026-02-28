"""Add image_generation and video_generation model types

Revision ID: 014_add_generation_model_types
Revises: 013_add_product_tables
Create Date: 2026-02-28

Description:
    扩展 model_type 支持 image_generation 和 video_generation 类型。
"""

from alembic import op

revision = "014_add_generation_model_types"
down_revision = "013_add_product_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "COMMENT ON COLUMN model_configs.model_type IS '模型类型(llm/embedding/rerank/image_generation/video_generation)'"
    )


def downgrade():
    op.execute(
        "COMMENT ON COLUMN model_configs.model_type IS '模型类型(llm/embedding/rerank)'"
    )
