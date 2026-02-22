#!/bin/bash
###############################################################################
# 服务器初始化脚本
# 用途: 在Jenkins服务器上准备部署环境
# 使用: sudo bash scripts/init-deployment.sh
###############################################################################

set -e

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INIT]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

###############################################################################
# 配置变量
###############################################################################

DEPLOY_DIR="/opt/ecom-chat-bot"
NETWORK_NAME="ecom-network"
PROJECT_USER="${SUDO_USER:-${USER}}"

###############################################################################
# 主流程
###############################################################################

log "=========================================="
log "服务器部署环境初始化"
log "=========================================="
info "部署目录: ${DEPLOY_DIR}"
info "当前用户: ${PROJECT_USER}"
log "=========================================="
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then
    error "请使用 sudo 运行此脚本"
fi

###############################################################################
# 1. 创建目录结构
###############################################################################

log "步骤 1/8: 创建目录结构"

mkdir -p ${DEPLOY_DIR}/{shared/logs,releases,backups}

info "目录结构:"
tree -L 2 ${DEPLOY_DIR} 2>/dev/null || ls -la ${DEPLOY_DIR}

log "✓ 目录创建完成"
echo ""

###############################################################################
# 2. 设置目录权限
###############################################################################

log "步骤 2/8: 设置目录权限"

# 设置jenkins用户权限（如果存在）
if id "jenkins" &>/dev/null; then
    info "设置jenkins用户权限..."
    chown -R jenkins:jenkins ${DEPLOY_DIR}
    log "✓ jenkins用户权限已设置"
else
    warn "jenkins用户不存在，跳过权限设置"
    chown -R ${PROJECT_USER}:${PROJECT_USER} ${DEPLOY_DIR}
fi

chmod -R 755 ${DEPLOY_DIR}
chmod 700 ${DEPLOY_DIR}/shared

log "✓ 权限设置完成"
echo ""

###############################################################################
# 3. 创建生产环境配置
###############################################################################

log "步骤 3/8: 创建生产环境配置"

ENV_FILE="${DEPLOY_DIR}/shared/.env.production"

if [ -f "$ENV_FILE" ]; then
    warn "配置文件已存在: $ENV_FILE"
    read -p "是否覆盖? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "跳过配置文件创建"
        echo ""
        skip_env=true
    fi
fi

if [ "$skip_env" != "true" ]; then
    # 生成随机JWT密钥
    JWT_SECRET=$(openssl rand -base64 32)
    
    cat > "$ENV_FILE" <<EOF
# ============================================
# 生产环境配置
# 创建时间: $(date)
# ============================================

# ============ 基础配置 ============
ENVIRONMENT=production
DEBUG=false
APP_NAME=电商智能客服系统
APP_VERSION=1.0.0
API_V1_PREFIX=/api/v1

# ============ 安全配置 ============
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_HOURS=8
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# API Key配置
API_KEY_PREFIX=eck_
API_KEY_LENGTH=32

# ============ LLM配置 ============
LLM_PROVIDER=deepseek

# DeepSeek配置
DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OpenAI配置（备用）
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o

# ============ 日志配置 ============
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============ CORS配置 ============
CORS_ORIGINS=["http://localhost:3000","http://115.190.75.88"]

# ============ 限流配置 ============
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# ============ 监控配置 ============
ENABLE_METRICS=true
ENABLE_TRACING=false
EOF

    chmod 600 "$ENV_FILE"
    
    log "✓ 配置文件已创建: $ENV_FILE"
    warn "⚠️  请根据实际情况修改配置文件中的敏感信息"
fi

echo ""

###############################################################################
# 4. 创建Docker网络
###############################################################################

log "步骤 4/8: 创建Docker网络"

if docker network ls | grep -q "$NETWORK_NAME"; then
    info "Docker网络已存在: $NETWORK_NAME"
else
    docker network create "$NETWORK_NAME"
    log "✓ Docker网络创建成功: $NETWORK_NAME"
fi

echo ""

###############################################################################
# 5. 检查基础服务
###############################################################################

log "步骤 5/8: 检查基础服务"

info "检查PostgreSQL..."
if docker ps | grep -q "ecom-chatbot-postgres"; then
    log "✓ PostgreSQL 运行中"
else
    warn "PostgreSQL 未运行"
    info "提示: 需要先启动基础服务"
    info "命令: cd /path/to/project && docker-compose up -d postgres redis milvus rabbitmq"
fi

info "检查Redis..."
if docker ps | grep -q "ecom-chatbot-redis"; then
    log "✓ Redis 运行中"
else
    warn "Redis 未运行"
fi

info "检查Milvus..."
if docker ps | grep -q "ecom-chatbot-milvus"; then
    log "✓ Milvus 运行中"
else
    warn "Milvus 未运行"
fi

info "检查RabbitMQ..."
if docker ps | grep -q "ecom-chatbot-rabbitmq"; then
    log "✓ RabbitMQ 运行中"
else
    warn "RabbitMQ 未运行"
fi

echo ""

###############################################################################
# 6. 创建日志轮转配置
###############################################################################

log "步骤 6/8: 配置日志轮转"

LOGROTATE_CONF="/etc/logrotate.d/ecom-chatbot"

cat > "$LOGROTATE_CONF" <<EOF
${DEPLOY_DIR}/shared/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 jenkins jenkins
    sharedscripts
    postrotate
        docker kill -s USR1 ecom-chatbot-api 2>/dev/null || true
    endscript
}
EOF

log "✓ 日志轮转配置已创建"
echo ""

###############################################################################
# 7. 创建部署脚本软链接
###############################################################################

log "步骤 7/8: 创建部署脚本"

# 假设项目在当前用户的工作目录
PROJECT_DIR="${PWD}"
if [ -f "${PROJECT_DIR}/scripts/jenkins-deploy.sh" ]; then
    cp "${PROJECT_DIR}/scripts/jenkins-deploy.sh" "${DEPLOY_DIR}/"
    cp "${PROJECT_DIR}/scripts/smoke-test.sh" "${DEPLOY_DIR}/"
    chmod +x ${DEPLOY_DIR}/*.sh
    log "✓ 部署脚本已复制"
else
    warn "未找到部署脚本，请手动复制"
fi

echo ""

###############################################################################
# 8. 验证环境
###############################################################################

log "步骤 8/8: 验证环境"

info "检查Docker..."
docker --version || error "Docker未安装"

info "检查Docker Compose..."
docker-compose --version || docker compose version || warn "Docker Compose不可用"

info "检查磁盘空间..."
df -h ${DEPLOY_DIR}

info "检查网络连接..."
if curl -s -m 5 https://api.deepseek.com > /dev/null; then
    log "✓ 网络连接正常"
else
    warn "网络连接可能异常"
fi

echo ""

###############################################################################
# 完成
###############################################################################

log "=========================================="
log "✅ 初始化完成！"
log "=========================================="
echo ""

info "📁 部署目录结构:"
tree -L 2 ${DEPLOY_DIR} 2>/dev/null || ls -la ${DEPLOY_DIR}

echo ""
info "📝 下一步操作:"
echo "  1. 检查并修改配置文件:"
echo "     sudo vi ${ENV_FILE}"
echo ""
echo "  2. 启动基础服务（如果未运行）:"
echo "     cd /path/to/project"
echo "     docker-compose up -d postgres redis milvus rabbitmq"
echo ""
echo "  3. 在Jenkins中配置流水线:"
echo "     - 创建 Pipeline Job"
echo "     - SCM: Git (develop分支)"
echo "     - Script Path: Jenkinsfile"
echo ""
echo "  4. 配置Git Webhook:"
echo "     - URL: http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token"
echo "     - Events: Push events"
echo "     - Branch: develop"
echo ""

log "=========================================="

exit 0
