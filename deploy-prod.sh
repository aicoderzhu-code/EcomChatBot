#!/bin/bash
set -e

echo "🚀 部署生产环境..."

# 设置环境变量
export DEPLOY_ENV=production

# 检查SSL证书
if [ ! -f "./ssl/cert.pem" ] || [ ! -f "./ssl/key.pem" ]; then
    echo "❌ 错误：SSL证书文件不存在！"
    echo "请将证书文件放置在 ./ssl/ 目录下："
    echo "  - cert.pem"
    echo "  - key.pem"
    exit 1
fi

echo "SSL证书检查通过 ✓"

# 构建并启动服务
echo "正在构建Docker镜像..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

echo "正在启动服务..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo ""
echo "✅ 生产环境部署完成！"
echo "访问地址: https://ecomchat.cn"
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
