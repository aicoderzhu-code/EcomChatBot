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

# 启动应用
echo "🎉 启动应用服务..."
exec "$@"
