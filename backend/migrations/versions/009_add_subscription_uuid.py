"""add subscription_id uuid field

Revision ID: 009
Revises: 008
Create Date: 2026-02-24
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 添加列（允许 NULL，后面填充数据再加约束）
    op.add_column(
        "subscriptions",
        sa.Column("subscription_id", sa.String(36), nullable=True, comment="订阅唯一标识(UUID)"),
    )

    # 2. 给现有记录填充 UUID
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id FROM subscriptions")).fetchall()
    for row in rows:
        conn.execute(
            text("UPDATE subscriptions SET subscription_id = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": row[0]},
        )

    # 3. 改为 NOT NULL + UNIQUE
    op.alter_column("subscriptions", "subscription_id", nullable=False)
    op.create_unique_constraint("uq_subscription_id", "subscriptions", ["subscription_id"])
    op.create_index("idx_subscription_uuid", "subscriptions", ["subscription_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_subscription_uuid", table_name="subscriptions")
    op.drop_constraint("uq_subscription_id", "subscriptions", type_="unique")
    op.drop_column("subscriptions", "subscription_id")
