#!/bin/bash
set -e

echo "🚀 启动 ecom-chatbot 服务..."

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL 尚未就绪，等待中..."
  sleep 2
done
echo "✅ PostgreSQL 已就绪"

# 检查是否需要初始化数据库
if [ "$RUN_INIT_DB" = "true" ]; then
    echo "📦 初始化数据库..."
    python init_db.py
    if [ $? -eq 0 ]; then
        echo "✅ 数据库初始化完成"
    else
        echo "❌ 数据库初始化失败"
        exit 1
    fi
fi

# 运行数据库迁移
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 运行数据库迁移..."
    alembic upgrade head
    if [ $? -eq 0 ]; then
        echo "✅ 数据库迁移完成"
    else
        echo "❌ 数据库迁移失败"
        exit 1
    fi
fi

# 执行 schema 同步（确保 create_all 生成的表与迁移脚本一致）
if [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_DB" ]; then
    echo "🔄 执行 schema 同步..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=0 -c "
        -- conversations 表补列（迁移 002）
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolved INTEGER DEFAULT 0;
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(20);
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS transferred_to_human INTEGER DEFAULT 0;
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS transfer_reason VARCHAR(255);
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS resolution_time INTEGER;
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT;
        -- subscriptions 表删除废弃的 quota 列（迁移 012）
        ALTER TABLE subscriptions DROP COLUMN IF EXISTS conversation_quota;
        ALTER TABLE subscriptions DROP COLUMN IF EXISTS api_quota;
        ALTER TABLE subscriptions DROP COLUMN IF EXISTS storage_quota;
        ALTER TABLE subscriptions DROP COLUMN IF EXISTS concurrent_quota;
        -- 字段长度扩展（迁移 004/011），确保与迁移一致
        ALTER TABLE model_configs ALTER COLUMN api_key TYPE VARCHAR(512);
        ALTER TABLE platform_configs ALTER COLUMN app_secret TYPE VARCHAR(512);
        -- 清理孤立表（迁移 012 删除）
        DROP TABLE IF EXISTS usage_records;
        DROP TABLE IF EXISTS quota_adjustment_logs;
    " 2>/dev/null && echo "✅ Schema 同步完成" || echo "⚠️  Schema 同步跳过"
fi

# 启动应用
echo "🎉 启动应用服务..."
exec "$@"
