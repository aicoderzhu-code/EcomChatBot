#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - 状态检查脚本
##############################################

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 检查 Docker Compose 命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║         电商智能客服 SaaS 平台 - 服务状态              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

log_info "服务状态:"
$DOCKER_COMPOSE_CMD ps
echo ""

log_info "容器资源使用情况:"
docker stats --no-stream $(docker ps --filter name=ecom-chatbot -q) 2>/dev/null || echo "无运行中的容器"
echo ""

log_info "磁盘使用情况:"
docker system df
echo ""
