#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - 停止脚本
##############################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 检查 Docker Compose 命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║         停止电商智能客服 SaaS 平台服务                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 询问是否删除数据卷
read -p "是否同时删除数据卷（将清空所有数据）？[y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_warning "停止服务并删除数据卷..."
    $DOCKER_COMPOSE_CMD down -v
    log_success "服务已停止，数据卷已删除"
else
    log_info "停止服务（保留数据）..."
    $DOCKER_COMPOSE_CMD down
    log_success "服务已停止，数据已保留"
fi

echo ""
log_info "如需重新启动，请运行: ./deploy.sh"
echo ""
