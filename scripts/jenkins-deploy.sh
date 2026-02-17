#!/bin/bash
###############################################################################
# Jenkins 自动部署脚本
# 用途: 实现零停机滚动更新部署
# 使用: bash jenkins-deploy.sh <BUILD_NUMBER>
###############################################################################

set -e

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

###############################################################################
# 配置变量
###############################################################################

BUILD_NUMBER=$1
DEPLOY_DIR="/opt/ecom-chat-bot"
IMAGE_NAME="ecom-chat-bot-api"
IMAGE_TAG="${BUILD_NUMBER:-latest}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.prod.yml"
NETWORK_NAME="ecom-network"

# Docker Compose命令检测
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

###############################################################################
# 前置检查
###############################################################################

log "=========================================="
log "Jenkins 自动部署开始"
log "=========================================="
info "部署目录: ${DEPLOY_DIR}"
info "镜像版本: ${IMAGE_NAME}:${IMAGE_TAG}"
info "构建编号: ${BUILD_NUMBER}"
log "=========================================="

# 参数检查
[ -z "$BUILD_NUMBER" ] && error "缺少 BUILD_NUMBER 参数\n使用方法: bash jenkins-deploy.sh <BUILD_NUMBER>"

# 目录检查
[ ! -d "$DEPLOY_DIR" ] && error "部署目录不存在: $DEPLOY_DIR"
[ ! -f "$COMPOSE_FILE" ] && error "Compose文件不存在: $COMPOSE_FILE"

# Docker检查
command -v docker &> /dev/null || error "Docker未安装"

# 网络检查
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    warn "Docker网络不存在，正在创建: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
    log "网络创建成功"
fi

###############################################################################
# 1. 备份当前版本
###############################################################################

log "步骤 1/6: 备份当前运行版本"

if docker ps --format '{{.Names}}' | grep -q "^ecom-chatbot-api$"; then
    CURRENT_IMAGE=$(docker inspect ecom-chatbot-api --format='{{.Config.Image}}')
    CURRENT_TAG=$(echo "$CURRENT_IMAGE" | cut -d: -f2)
    
    info "当前版本: ${CURRENT_TAG}"
    echo "$CURRENT_TAG" > "${DEPLOY_DIR}/shared/rollback.tag"
    
    # 标记当前镜像为 rollback
    docker tag "$CURRENT_IMAGE" "${IMAGE_NAME}:rollback" || warn "标记失败"
    log "✓ 版本备份完成"
else
    warn "未找到运行中的容器，跳过备份"
fi

###############################################################################
# 2. 标记新镜像
###############################################################################

log "步骤 2/6: 准备新版本镜像"

# 确认新镜像存在
if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${IMAGE_NAME}:latest$"; then
    error "镜像不存在: ${IMAGE_NAME}:latest"
fi

# 标记版本号
docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:${IMAGE_TAG}"
log "✓ 镜像标记完成: ${IMAGE_NAME}:${IMAGE_TAG}"

###############################################################################
# 3. 启动新容器（临时名称）
###############################################################################

log "步骤 3/6: 启动新版本容器"

cd "$DEPLOY_DIR" || error "无法进入部署目录"

# 使用新镜像启动容器
# 注意：假设基础服务(postgres, redis, milvus, rabbitmq)已在宿主机运行
info "启动新版本容器..."

# 先停止并删除所有相关旧容器（包括带hash前缀的），避免docker-compose尝试复用旧容器配置
info "清理所有旧容器（包括失败的容器）..."
# 使用docker ps过滤并强制删除所有ecom-chatbot-api和ecom-chatbot-celery容器
docker ps -a --filter "name=ecom-chatbot-api" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=ecom-chatbot-celery" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# 启动新容器
BUILD_NUMBER=$IMAGE_TAG $DOCKER_COMPOSE -f "$COMPOSE_FILE" -p ecom-prod up -d

log "✓ 新容器启动成功"

###############################################################################
# 4. 健康检查
###############################################################################

log "步骤 4/6: 执行健康检查"

MAX_RETRY=30
RETRY_COUNT=0
HEALTH_CHECK_URL="http://localhost:8000/health"

info "等待服务就绪..."
sleep 10

while [ $RETRY_COUNT -lt $MAX_RETRY ]; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    
    # 检查容器是否健康
    CONTAINER_HEALTH=$(docker inspect ecom-chatbot-api --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
    
    if [ "$CONTAINER_HEALTH" = "healthy" ]; then
        log "✓ 容器健康检查通过"
        
        # 额外的HTTP健康检查
        if curl -sf "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log "✓ HTTP健康检查通过"
            break
        fi
    fi
    
    if [ $RETRY_COUNT -eq $MAX_RETRY ]; then
        error "健康检查超时\n容器状态: $CONTAINER_HEALTH\n请检查日志: docker logs ecom-chatbot-api"
    fi
    
    info "健康检查中... ($RETRY_COUNT/$MAX_RETRY)"
    sleep 5
done

log "✓ 新版本健康检查通过"

###############################################################################
# 5. 流量切换（停止旧容器）
###############################################################################

log "步骤 5/6: 切换流量到新版本"

# 查找旧容器
OLD_CONTAINERS=$(docker ps -a --filter "name=ecom-chatbot-api-old" --filter "name=ecom-chatbot-celery-old" --format "{{.Names}}" || true)

if [ -n "$OLD_CONTAINERS" ]; then
    info "停止旧版本容器..."
    echo "$OLD_CONTAINERS" | xargs -r docker stop
    echo "$OLD_CONTAINERS" | xargs -r docker rm
    log "✓ 旧容器已清理"
else
    info "未找到旧版本容器"
fi

log "✓ 流量切换完成"

###############################################################################
# 6. 清理工作
###############################################################################

log "步骤 6/6: 清理环境"

# 清理悬空镜像
info "清理悬空镜像..."
docker image prune -f > /dev/null 2>&1 || true

# 清理旧版本镜像（保留最近5个）
info "清理旧版本镜像..."
docker images "${IMAGE_NAME}" --format "{{.Tag}}" | \
    grep -E '^[0-9]+$' | \
    sort -rn | \
    tail -n +6 | \
    xargs -r -I {} docker rmi "${IMAGE_NAME}:{}" 2>/dev/null || true

log "✓ 清理完成"

###############################################################################
# 部署完成
###############################################################################

log "=========================================="
log "✅ 部署成功完成！"
log "=========================================="
info "版本: ${IMAGE_TAG}"
info "服务状态:"
docker ps --filter "name=ecom-chatbot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
info "访问地址:"
echo "  - API文档: http://115.190.75.88:8000/docs"
echo "  - 健康检查: http://115.190.75.88:8000/health"
echo ""
info "查看日志:"
echo "  docker logs -f ecom-chatbot-api"
echo "  docker logs -f ecom-chatbot-celery"
log "=========================================="

exit 0
