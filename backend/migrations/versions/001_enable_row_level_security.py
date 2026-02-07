"""Enable Row Level Security (RLS) for tenant isolation

Revision ID: 001_rls
Revises:
Create Date: 2026-02-06

Description:
    为所有租户相关表启用 PostgreSQL 行级安全（Row Level Security），
    在数据库层面强制实现租户数据隔离，防止数据泄露。

    启用 RLS 的表：
    - conversations (对话)
    - messages (消息)
    - knowledge_bases (知识库)
    - webhook_configs (Webhook配置)
    - webhook_logs (Webhook日志)
    - usage_records (用量记录)
    - bills (账单)
    - payment_orders (支付订单)

    策略说明：
    - 每个租户只能访问自己的数据（通过 tenant_id 过滤）
    - 系统管理员可以访问所有数据（通过 current_setting 判断）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_rls'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """启用 RLS 策略"""

    # 设置当前租户ID的函数（通过 session 变量传递）
    op.execute("""
        -- 创建函数：获取当前租户ID
        CREATE OR REPLACE FUNCTION get_current_tenant_id()
        RETURNS UUID AS $$
        DECLARE
            tenant_id_str TEXT;
        BEGIN
            -- 从 session 配置中获取 tenant_id
            -- 应用层在执行查询前设置: SET LOCAL app.current_tenant_id = 'xxx'
            tenant_id_str := current_setting('app.current_tenant_id', TRUE);

            IF tenant_id_str IS NULL OR tenant_id_str = '' THEN
                RETURN NULL;
            END IF;

            RETURN tenant_id_str::UUID;
        EXCEPTION
            WHEN OTHERS THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # 创建函数：检查是否为系统管理员
    op.execute("""
        CREATE OR REPLACE FUNCTION is_system_admin()
        RETURNS BOOLEAN AS $$
        DECLARE
            is_admin_str TEXT;
        BEGIN
            -- 从 session 配置中获取管理员标志
            -- 管理员操作时设置: SET LOCAL app.is_admin = 'true'
            is_admin_str := current_setting('app.is_admin', TRUE);

            RETURN is_admin_str = 'true';
        EXCEPTION
            WHEN OTHERS THEN
                RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # ==================== 对话相关表 ====================

    # conversations 表
    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY conversations_isolation ON conversations
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # messages 表
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY messages_isolation ON messages
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # ==================== 知识库相关表 ====================

    # knowledge_bases 表
    op.execute("ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY knowledge_bases_isolation ON knowledge_bases
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # ==================== Webhook 相关表 ====================

    # webhook_configs 表
    op.execute("ALTER TABLE webhook_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY webhook_configs_isolation ON webhook_configs
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # webhook_logs 表（通过 webhook_configs 关联）
    op.execute("ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY webhook_logs_isolation ON webhook_logs
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM webhook_configs
                WHERE webhook_configs.webhook_id = webhook_logs.webhook_id
                AND webhook_configs.tenant_id = get_current_tenant_id()
            )
            OR is_system_admin()
        )
    """)

    # ==================== 计费相关表 ====================

    # usage_records 表
    op.execute("ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY usage_records_isolation ON usage_records
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # bills 表
    op.execute("ALTER TABLE bills ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY bills_isolation ON bills
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # ==================== 支付相关表 ====================

    # payment_orders 表
    op.execute("ALTER TABLE payment_orders ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY payment_orders_isolation ON payment_orders
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    # ==================== 订阅相关表 ====================

    # subscriptions 表
    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY subscriptions_isolation ON subscriptions
        FOR ALL
        USING (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
        WITH CHECK (
            tenant_id = get_current_tenant_id()
            OR is_system_admin()
        )
    """)

    print("✅ Row Level Security (RLS) 策略已启用")
    print("   受保护的表:")
    print("   - conversations, messages")
    print("   - knowledge_bases")
    print("   - webhook_configs, webhook_logs")
    print("   - usage_records, bills")
    print("   - payment_orders")
    print("   - subscriptions")


def downgrade():
    """禁用 RLS 策略"""

    # 删除所有 RLS 策略
    tables = [
        'conversations',
        'messages',
        'knowledge_bases',
        'webhook_configs',
        'webhook_logs',
        'usage_records',
        'bills',
        'payment_orders',
        'subscriptions',
    ]

    for table in tables:
        # 删除策略
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        # 禁用 RLS
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 删除辅助函数
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant_id()")
    op.execute("DROP FUNCTION IF EXISTS is_system_admin()")

    print("✅ Row Level Security (RLS) 策略已禁用")