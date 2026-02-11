"""Add missing columns to conversations table

Revision ID: 002_conversations
Revises: 001_rls
Create Date: 2026-02-11

Description:
    为 conversations 表添加模型定义中缺失的列：
    - resolved: 是否解决问题
    - resolution_type: 解决方式(ai/human/timeout/abandoned)
    - transferred_to_human: 是否转人工
    - transfer_reason: 转人工原因
    - resolution_time: 解决时长(秒)
    - summary: 对话摘要
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002_conversations'
down_revision = '001_rls'
branch_labels = None
depends_on = None


def upgrade():
    """添加 conversations 表缺失的列"""
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolved INTEGER DEFAULT 0")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(20)")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS transferred_to_human INTEGER DEFAULT 0")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS transfer_reason VARCHAR(255)")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolution_time INTEGER")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT")


def downgrade():
    """移除新增的列"""
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS resolved")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS resolution_type")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS transferred_to_human")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS transfer_reason")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS resolution_time")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS summary")
