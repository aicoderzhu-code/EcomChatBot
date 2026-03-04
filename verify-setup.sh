#!/bin/bash
# 环境配置验证脚本

echo "=========================================="
echo "环境配置验证"
echo "=========================================="
echo ""

# 检查必需文件
echo "1. 检查配置文件..."
files=(
    ".env.development"
    "backend/.env.development"
    "backend/.env.production"
    "frontend/.env.development"
    "frontend/.env.production"
    "nginx/conf.d/development.conf"
    "nginx/conf.d/ecomchat.conf"
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "docker-compose.prod.yml"
    "deploy-dev.sh"
    "deploy-prod.sh"
    "DEPLOYMENT.md"
)

missing_files=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失)"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo ""
    echo "❌ 有 $missing_files 个文件缺失！"
    exit 1
fi

echo ""
echo "2. 检查部署脚本权限..."
if [ -x "deploy-dev.sh" ] && [ -x "deploy-prod.sh" ]; then
    echo "  ✓ 部署脚本可执行"
else
    echo "  ✗ 部署脚本不可执行"
    echo "  运行: chmod +x deploy-dev.sh deploy-prod.sh"
    exit 1
fi

echo ""
echo "3. 检查开发环境配置..."
if grep -q "DEPLOY_ENV=development" .env.development; then
    echo "  ✓ DEPLOY_ENV 配置正确"
else
    echo "  ✗ DEPLOY_ENV 配置错误"
    exit 1
fi

host_ip=$(grep "HOST_IP=" .env.development | cut -d'=' -f2)
if [ -n "$host_ip" ]; then
    echo "  ✓ HOST_IP 已配置: $host_ip"
    if [ "$host_ip" = "192.168.1.100" ]; then
        echo "  ⚠️  警告: HOST_IP 使用默认值，请根据实际情况修改"
    fi
else
    echo "  ✗ HOST_IP 未配置"
    exit 1
fi

echo ""
echo "4. 检查后端配置文件..."
if grep -q "ENVIRONMENT=development" backend/.env.development; then
    echo "  ✓ 后端开发环境配置正确"
else
    echo "  ✗ 后端开发环境配置错误"
    exit 1
fi

if grep -q "ENVIRONMENT=production" backend/.env.production; then
    echo "  ✓ 后端生产环境配置正确"
else
    echo "  ✗ 后端生产环境配置错误"
    exit 1
fi

echo ""
echo "5. 检查前端配置文件..."
if grep -q "ws://192.168.1.100" frontend/.env.development; then
    echo "  ✓ 前端开发环境 WebSocket 配置正确"
else
    echo "  ✗ 前端开发环境 WebSocket 配置错误"
    exit 1
fi

if grep -q "wss://ecomchat.cn" frontend/.env.production; then
    echo "  ✓ 前端生产环境 WebSocket 配置正确"
else
    echo "  ✗ 前端生产环境 WebSocket 配置错误"
    exit 1
fi

echo ""
echo "6. 检查Nginx配置..."
if [ -f "nginx/conf.d/development.conf" ]; then
    if grep -q "listen 80" nginx/conf.d/development.conf && ! grep -q "listen 443" nginx/conf.d/development.conf; then
        echo "  ✓ 开发环境 Nginx 配置正确（HTTP only）"
    else
        echo "  ✗ 开发环境 Nginx 配置错误"
        exit 1
    fi
fi

if [ -f "nginx/conf.d/ecomchat.conf" ]; then
    if grep -q "listen 443 ssl" nginx/conf.d/ecomchat.conf; then
        echo "  ✓ 生产环境 Nginx 配置正确（HTTPS）"
    else
        echo "  ✗ 生产环境 Nginx 配置错误"
        exit 1
    fi
fi

echo ""
echo "7. 检查Docker Compose配置..."
if grep -q "docker-compose.dev.yml" deploy-dev.sh; then
    echo "  ✓ 开发部署脚本引用正确"
else
    echo "  ✗ 开发部署脚本引用错误"
    exit 1
fi

if grep -q "docker-compose.prod.yml" deploy-prod.sh; then
    echo "  ✓ 生产部署脚本引用正确"
else
    echo "  ✗ 生产部署脚本引用错误"
    exit 1
fi

echo ""
echo "8. 检查SSL证书（生产环境）..."
if [ -f "ssl/cert.pem" ] && [ -f "ssl/key.pem" ]; then
    echo "  ✓ SSL证书文件存在"
else
    echo "  ⚠️  警告: SSL证书文件不存在（生产环境部署时需要）"
    echo "     请将证书放置在 ./ssl/ 目录下"
fi

echo ""
echo "=========================================="
echo "✅ 验证完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 修改 .env.development 中的 HOST_IP 为你的本机IP"
echo "  2. 运行 ./deploy-dev.sh 部署开发环境"
echo "  3. 或运行 ./deploy-prod.sh 部署生产环境"
echo ""
echo "详细文档请查看: DEPLOYMENT.md"
