"""Add api_key_prefix column to tenants table for fast authentication

Revision ID: 003_api_key_prefix
Revises: 002_conversations
Create Date: 2026-02-14

Description:
    为 tenants 表添加 api_key_prefix 列和索引，用于快速 API Key 认证。

    性能优化说明：
    - 原方案：遍历所有租户进行 bcrypt 验证，O(n) 时间复杂度，505 个租户约 85 秒
    - 新方案：通过 api_key_prefix 索引直接查询，O(1) 时间复杂度，约 0.1 秒

    向后兼容：
    - 新字段允许为 NULL，旧租户首次认证成功后会自动填充
    - 新创建的租户会在创建时自动保存 api_key_prefix
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '003_api_key_prefix'
down_revision = '002_conversations'
branch_labels = None
depends_on = None


def upgrade():
    """添加 api_key_prefix 列和索引"""
    # 添加 api_key_prefix 列（允许为 NULL，旧租户首次认证时自动填充）
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS api_key_prefix VARCHAR(16)")

    # 创建索引用于快速查找
    op.execute("CREATE INDEX IF NOT EXISTS idx_tenant_api_key_prefix ON tenants (api_key_prefix)")


def downgrade():
    """移除 api_key_prefix 列和索引"""
    op.execute("DROP INDEX IF EXISTS idx_tenant_api_key_prefix")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS api_key_prefix")
