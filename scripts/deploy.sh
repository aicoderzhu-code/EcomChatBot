#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - 一键部署脚本
# 包含所有服务的 Docker 部署和数据库初始化
##############################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印横幅
print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║       电商智能客服 SaaS 平台 - 一键部署脚本             ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查 Docker 和 Docker Compose
check_requirements() {
    log_info "检查系统依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "未找到 Docker，请先安装 Docker"
        log_info "访问 https://docs.docker.com/get-docker/ 安装"
        exit 1
    fi
    log_success "Docker 已安装: $(docker --version)"
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "未找到 Docker Compose，请先安装"
        log_info "访问 https://docs.docker.com/compose/install/ 安装"
        exit 1
    fi
    
    # 检查是使用 docker-compose 还是 docker compose
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        log_success "Docker Compose 已安装: $(docker-compose --version)"
    else
        DOCKER_COMPOSE_CMD="docker compose"
        log_success "Docker Compose 已安装: $(docker compose version)"
    fi
}

# 检查环境变量文件
check_env_file() {
    log_info "检查环境变量配置..."
    
    if [ ! -f backend/.env ]; then
        if [ -f backend/.env.example ]; then
            log_warning "未找到 backend/.env 文件，从 .env.example 创建..."
            cp backend/.env.example backend/.env
            log_success "已创建 backend/.env 文件"
            log_warning "⚠️  请根据需要修改 backend/.env 中的配置（特别是密钥和密码）"
        else
            log_error "未找到 backend/.env.example 文件"
            exit 1
        fi
    else
        log_success "环境变量文件已存在"
    fi
}

# 清理旧容器和卷（可选）
cleanup_old_deployment() {
    read -p "是否清理旧的部署（删除容器和数据卷）？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_warning "正在清理旧部署..."
        $DOCKER_COMPOSE_CMD down -v 2>/dev/null || true
        log_success "清理完成"
    else
        log_info "跳过清理，将尝试更新现有部署"
    fi
}

# 构建 Docker 镜像
build_images() {
    log_info "构建 Docker 镜像..."
    $DOCKER_COMPOSE_CMD build --no-cache
    log_success "镜像构建完成"
}

# 启动基础服务
start_infrastructure() {
    log_info "启动基础服务（PostgreSQL、Redis、Milvus、RabbitMQ）..."
    $DOCKER_COMPOSE_CMD up -d postgres redis milvus-etcd milvus-minio milvus rabbitmq
    
    log_info "等待基础服务健康检查..."
    local max_wait=120
    local waited=0
    
    while [ $waited -lt $max_wait ]; do
        if $DOCKER_COMPOSE_CMD ps | grep -q "healthy"; then
            local healthy_count=$($DOCKER_COMPOSE_CMD ps | grep -c "healthy" || true)
            log_info "健康服务数: $healthy_count"
            
            # 检查关键服务是否健康
            if $DOCKER_COMPOSE_CMD ps postgres | grep -q "healthy" && \
               $DOCKER_COMPOSE_CMD ps redis | grep -q "healthy"; then
                log_success "基础服务已就绪"
                return 0
            fi
        fi
        
        sleep 5
        waited=$((waited + 5))
        echo -n "."
    done
    
    echo ""
    log_error "基础服务启动超时"
    log_info "查看服务状态:"
    $DOCKER_COMPOSE_CMD ps
    exit 1
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    $DOCKER_COMPOSE_CMD up db-init
    
    # 检查初始化是否成功
    if [ $? -eq 0 ]; then
        log_success "数据库初始化完成"
    else
        log_error "数据库初始化失败"
        log_info "查看初始化日志:"
        $DOCKER_COMPOSE_CMD logs db-init
        exit 1
    fi
}

# 启动应用服务
start_application() {
    log_info "启动应用服务..."
    $DOCKER_COMPOSE_CMD up -d api celery-worker
    log_success "应用服务已启动"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                  🎉 部署成功！                          ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "服务访问信息:"
    echo ""
    echo "  📡 API 服务:"
    echo "     - 主地址: http://localhost:8000"
    echo "     - API 文档: http://localhost:8000/docs"
    echo "     - ReDoc: http://localhost:8000/redoc"
    echo ""
    echo "  🗄️  数据库服务:"
    echo "     - PostgreSQL: localhost:5432"
    echo "       用户名: ecom_user"
    echo "       密码: ecom_password"
    echo "       数据库: ecom_chatbot"
    echo ""
    echo "  🔴 Redis: localhost:6379"
    echo ""
    echo "  🔍 Milvus: localhost:19530"
    echo ""
    echo "  🐰 RabbitMQ 管理界面: http://localhost:15672"
    echo "     用户名: guest"
    echo "     密码: guest"
    echo ""
    
    log_info "默认管理员账号:"
    echo "     用户名: admin"
    echo "     密码: admin123456"
    echo "     ⚠️  请立即修改默认密码！"
    echo ""
    
    log_info "常用命令:"
    echo "     查看日志: $DOCKER_COMPOSE_CMD logs -f [服务名]"
    echo "     停止服务: $DOCKER_COMPOSE_CMD stop"
    echo "     重启服务: $DOCKER_COMPOSE_CMD restart"
    echo "     完全停止: $DOCKER_COMPOSE_CMD down"
    echo ""
}

# 显示服务状态
show_service_status() {
    log_info "当前服务状态:"
    $DOCKER_COMPOSE_CMD ps
    echo ""
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 等待 API 服务完全启动
    sleep 10
    
    # 检查 API 健康
    if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
        log_success "API 服务健康检查通过"
    else
        log_warning "API 服务可能还在启动中，请稍后访问 http://localhost:8000/docs"
    fi
}

# 主函数
main() {
    print_banner
    
    # 1. 检查系统要求
    check_requirements
    
    # 2. 检查环境变量
    check_env_file
    
    # 3. 询问是否清理旧部署
    cleanup_old_deployment
    
    # 4. 构建镜像
    build_images
    
    # 5. 启动基础服务
    start_infrastructure
    
    # 6. 初始化数据库
    init_database
    
    # 7. 启动应用服务
    start_application
    
    # 8. 健康检查
    health_check
    
    # 9. 显示服务状态
    show_service_status
    
    # 10. 显示部署信息
    show_deployment_info
}

# 捕获中断信号
trap 'log_error "部署被中断"; exit 1' INT TERM

# 执行主函数
main

exit 0
