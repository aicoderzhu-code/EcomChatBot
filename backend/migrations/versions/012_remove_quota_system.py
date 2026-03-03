"""移除配额系统

Revision ID: 012_remove_quota_system
Revises: 011_encrypt_platform_secret
Create Date: 2026-02-28

移除对话/API/存储配额字段及相关追踪表，保留并发会话限制（系统配置）、
订阅时间起止日期、状态、plan_type（用于账单记录）。
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_remove_quota_system"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    # 删除 subscriptions 表的 4 个配额列
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS conversation_quota")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS api_quota")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS storage_quota")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS concurrent_quota")

    # 删除 bills.overage_fee
    op.execute("ALTER TABLE bills DROP COLUMN IF EXISTS overage_fee")

    # 删除两张配额相关表
    op.execute("DROP TABLE IF EXISTS usage_records")
    op.execute("DROP TABLE IF EXISTS quota_adjustment_logs")


def downgrade():
    # 恢复 quota_adjustment_logs 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS quota_adjustment_logs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id VARCHAR NOT NULL,
            quota_type VARCHAR NOT NULL,
            adjustment INTEGER NOT NULL,
            before_value INTEGER NOT NULL,
            after_value INTEGER NOT NULL,
            operator_id VARCHAR,
            operator_type VARCHAR,
            reason TEXT,
            ip_address VARCHAR,
            user_agent TEXT,
            extra_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # 恢复 usage_records 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            id BIGSERIAL PRIMARY KEY,
            tenant_id VARCHAR NOT NULL,
            record_date DATE NOT NULL,
            conversation_count INTEGER DEFAULT 0,
            input_tokens BIGINT DEFAULT 0,
            output_tokens BIGINT DEFAULT 0,
            storage_used FLOAT DEFAULT 0,
            api_calls INTEGER DEFAULT 0,
            overage_fee FLOAT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # 恢复 bills.overage_fee
    op.execute("ALTER TABLE bills ADD COLUMN IF NOT EXISTS overage_fee FLOAT DEFAULT 0")

    # 恢复 subscriptions 配额列
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS conversation_quota INTEGER DEFAULT 100")
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS api_quota INTEGER DEFAULT 1000")
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS storage_quota INTEGER DEFAULT 100")
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS concurrent_quota INTEGER DEFAULT 1")
