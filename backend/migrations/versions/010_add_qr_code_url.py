"""add qr_code_url to payment_orders

Revision ID: 010
Revises: 009
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_orders",
        sa.Column("qr_code_url", sa.Text(), nullable=True, comment="二维码URL，用于前端展示"),
    )


def downgrade() -> None:
    op.drop_column("payment_orders", "qr_code_url")
