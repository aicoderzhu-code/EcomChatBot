#!/bin/bash
# 快速启动脚本

set -e

echo "================================"
echo "电商智能客服系统 - 快速启动"
echo "================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 请先安装 Docker Compose"
    exit 1
fi

# 检查 .env 文件
if [ ! -f backend/.env ]; then
    echo "创建 .env 文件..."
    cp backend/.env.example backend/.env
    echo "✓ 已创建 backend/.env 文件，请根据需要修改配置"
fi

# 启动服务
echo ""
echo "启动 Docker 服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "等待服务启动（30秒）..."
sleep 30

# 检查服务状态
echo ""
echo "检查服务状态..."
docker-compose ps

# 初始化数据库
echo ""
echo "初始化数据库..."
docker-compose exec -T api alembic upgrade head

echo ""
echo "================================"
echo "✓ 启动完成！"
echo "================================"
echo ""
echo "服务地址："
echo "  - API 文档: http://localhost:8000/docs"
echo "  - API 服务: http://localhost:8000"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Milvus: localhost:19530"
echo "  - RabbitMQ 管理界面: http://localhost:15672"
echo ""
echo "查看日志："
echo "  docker-compose logs -f api"
echo ""
echo "停止服务："
echo "  docker-compose down"
echo ""
