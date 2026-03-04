#!/bin/bash
set -e

echo "🚀 部署开发环境..."

# 设置环境变量
export DEPLOY_ENV=development

# 提示用户配置IP
echo "请确保 .env.development 中的 HOST_IP 已配置为本机IP地址"
echo "当前配置的IP: $(grep HOST_IP .env.development | cut -d'=' -f2)"
read -p "按Enter继续，或按Ctrl+C取消..."

# 构建并启动服务
echo "正在构建Docker镜像..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml build

echo "正在启动服务..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

echo ""
echo "✅ 开发环境部署完成！"
echo "访问地址: http://$(grep HOST_IP .env.development | cut -d'=' -f2)"
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
