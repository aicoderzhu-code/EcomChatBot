"""Add time-based subscription plans

Revision ID: 008_subscription_plans
Revises: 007_add_platform
Create Date: 2026-02-24

Description:
    - 无需修改表结构（plan_type 已是 String，expire_at 已存在）
    - 将现有 free 订阅的 plan_type 更新为 trial（可选）
"""
from alembic import op


revision = '008_subscription_plans'
down_revision = '007_add_platform'
branch_labels = None
depends_on = None


def upgrade():
    # 将现有 free 试用订阅更新为 trial（is_trial=True 的记录）
    op.execute("""
        UPDATE subscriptions
        SET plan_type = 'trial'
        WHERE plan_type = 'free' AND is_trial = 1
    """)


def downgrade():
    op.execute("""
        UPDATE subscriptions
        SET plan_type = 'free'
        WHERE plan_type = 'trial'
    """)
