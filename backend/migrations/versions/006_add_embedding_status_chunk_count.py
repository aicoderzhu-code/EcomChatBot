"""Add embedding_status and chunk_count to knowledge_base

Revision ID: 006_add_embedding_status_chunk_count
Revises: 005_knowledge_settings
"""
from alembic import op

revision = '006_add_embedding_status_chunk_count'
down_revision = '005_knowledge_settings'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE knowledge_base
            ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS chunk_count INTEGER NOT NULL DEFAULT 1
    """)


def downgrade():
    op.execute("""
        ALTER TABLE knowledge_base
            DROP COLUMN IF EXISTS embedding_status,
            DROP COLUMN IF EXISTS chunk_count
    """)
