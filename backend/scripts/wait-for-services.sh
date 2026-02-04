#!/bin/bash
# 等待所有依赖服务就绪

set -e

echo "⏳ 等待依赖服务启动..."
echo ""

# 等待 PostgreSQL
echo "📦 检查 PostgreSQL..."
until pg_isready -h postgres -U ecom_user > /dev/null 2>&1; do
  echo "  PostgreSQL 未就绪，等待..."
  sleep 2
done
echo "✓ PostgreSQL 就绪"
echo ""

# 等待 Redis
echo "📦 检查 Redis..."
until redis-cli -h redis ping > /dev/null 2>&1; do
  echo "  Redis 未就绪，等待..."
  sleep 2
done
echo "✓ Redis 就绪"
echo ""

# 等待 Milvus
echo "📦 检查 Milvus..."
until curl -f http://milvus:9091/healthz > /dev/null 2>&1; do
  echo "  Milvus 未就绪，等待..."
  sleep 5
done
echo "✓ Milvus 就绪"
echo ""

# 等待 RabbitMQ
echo "📦 检查 RabbitMQ..."
until curl -f http://rabbitmq:15672 > /dev/null 2>&1; do
  echo "  RabbitMQ 未就绪，等待..."
  sleep 2
done
echo "✓ RabbitMQ 就绪"
echo ""

echo "✅ 所有依赖服务已就绪！"
