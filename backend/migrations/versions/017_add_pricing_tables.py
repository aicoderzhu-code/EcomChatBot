"""Add competitor_products and pricing_analyses tables

Revision ID: 017_add_pricing_tables
Revises: 016_add_generation_tables
Create Date: 2026-02-28

Description:
    - 创建 competitor_products 表（竞品数据）
    - 创建 pricing_analyses 表（定价分析结果）
"""

from alembic import op

revision = "017_add_pricing_tables"
down_revision = "016_add_generation_tables"
branch_labels = None
depends_on = None


def upgrade():
    # 创建 competitor_products 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS competitor_products (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            product_id INTEGER NOT NULL,
            competitor_name VARCHAR(256) NOT NULL,
            competitor_platform VARCHAR(64),
            competitor_url VARCHAR(1024),
            competitor_price NUMERIC(10, 2) NOT NULL,
            competitor_sales INTEGER DEFAULT 0,
            last_checked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_competitor_tenant ON competitor_products (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_competitor_product ON competitor_products (product_id)")

    # 创建 pricing_analyses 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS pricing_analyses (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            product_id INTEGER NOT NULL,
            current_price NUMERIC(10, 2) NOT NULL,
            suggested_price NUMERIC(10, 2) NOT NULL,
            min_price NUMERIC(10, 2),
            max_price NUMERIC(10, 2),
            strategy VARCHAR(32) NOT NULL DEFAULT 'competitive',
            competitor_count INTEGER DEFAULT 0,
            competitor_avg_price NUMERIC(10, 2),
            analysis_summary TEXT,
            analysis_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_pricing_tenant ON pricing_analyses (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pricing_product ON pricing_analyses (product_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS pricing_analyses")
    op.execute("DROP TABLE IF EXISTS competitor_products")
