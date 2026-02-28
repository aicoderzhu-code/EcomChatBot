"""Add orders and analysis_reports tables

Revision ID: 018_add_order_tables
Revises: 017_add_pricing_tables
Create Date: 2026-02-28

Description:
    - 创建 orders 表（订单数据）
    - 创建 analysis_reports 表（分析报告）
"""

from alembic import op

revision = "018_add_order_tables"
down_revision = "017_add_pricing_tables"
branch_labels = None
depends_on = None


def upgrade():
    # 创建 orders 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            platform_config_id INTEGER NOT NULL,
            platform_order_id VARCHAR(128) NOT NULL,
            product_id INTEGER,
            product_title VARCHAR(512) DEFAULT '',
            buyer_id VARCHAR(128) DEFAULT '',
            quantity INTEGER DEFAULT 1,
            unit_price NUMERIC(10, 2) DEFAULT 0,
            total_amount NUMERIC(10, 2) DEFAULT 0,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            paid_at TIMESTAMP,
            shipped_at TIMESTAMP,
            completed_at TIMESTAMP,
            refund_amount NUMERIC(10, 2),
            platform_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_order_tenant ON orders (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_platform ON orders (platform_config_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_status ON orders (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_product ON orders (product_id)")

    # 创建 analysis_reports 表
    op.execute("""
        CREATE TABLE IF NOT EXISTS analysis_reports (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            report_type VARCHAR(32) NOT NULL,
            title VARCHAR(256) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            period_start TIMESTAMP,
            period_end TIMESTAMP,
            summary TEXT,
            statistics TEXT,
            charts_data TEXT,
            file_url VARCHAR(1024),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_report_tenant ON analysis_reports (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_type ON analysis_reports (report_type)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS analysis_reports")
    op.execute("DROP TABLE IF EXISTS orders")
