#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - 查看日志脚本
##############################################

# 检查 Docker Compose 命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

# 如果提供了服务名，只查看该服务的日志
if [ -n "$1" ]; then
    echo "查看 $1 服务日志（Ctrl+C 退出）..."
    $DOCKER_COMPOSE_CMD logs -f "$1"
else
    echo "查看所有服务日志（Ctrl+C 退出）..."
    $DOCKER_COMPOSE_CMD logs -f
fi
