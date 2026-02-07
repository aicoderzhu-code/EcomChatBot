#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - API测试运行脚本
##############################################

set -e

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
    echo "║       电商智能客服 SaaS 平台 - API测试套件              ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."

    # 检查Docker服务
    if ! docker-compose ps api | grep -q "Up"; then
        log_error "API服务未运行，请先启动服务: docker-compose up -d"
        exit 1
    fi

    log_success "服务运行正常"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python 3，请先安装"
        exit 1
    fi

    log_success "Python 3 已安装: $(python3 --version)"
}

# 安装依赖
install_dependencies() {
    log_info "检查测试依赖..."

    if ! python3 -c "import pytest" 2>/dev/null; then
        log_warning "pytest未安装，正在安装..."
        pip3 install pytest requests pytest-html
        log_success "依赖安装完成"
    else
        log_success "测试依赖已满足"
    fi
}

# 测试API连通性
test_connectivity() {
    log_info "测试API连通性..."

    if curl --noproxy "*" -sf http://localhost:8000/health > /dev/null; then
        log_success "API连接正常"
    else
        log_error "无法连接到API服务，请检查服务状态"
        exit 1
    fi
}

# 运行测试
run_tests() {
    local test_type=$1

    log_info "开始运行测试..."
    echo ""

    cd backend

    case $test_type in
        "all")
            log_info "运行所有测试 (103个测试用例)"
            pytest tests/test_api_comprehensive.py -v --tb=short
            ;;
        "health")
            log_info "运行健康检查测试"
            pytest tests/test_api_comprehensive.py::TestHealthChecks -v
            ;;
        "admin")
            log_info "运行管理员接口测试"
            pytest tests/test_api_comprehensive.py::TestAdminAPIs -v
            ;;
        "tenant")
            log_info "运行租户接口测试"
            pytest tests/test_api_comprehensive.py::TestTenantAuthAPIs -v
            ;;
        "conversation")
            log_info "运行对话管理测试"
            pytest tests/test_api_comprehensive.py::TestConversationAPIs -v
            ;;
        "ai")
            log_info "运行AI对话测试"
            pytest tests/test_api_comprehensive.py::TestAIChatAPIs -v
            ;;
        "knowledge")
            log_info "运行知识库测试"
            pytest tests/test_api_comprehensive.py::TestKnowledgeAPIs -v
            ;;
        "report")
            log_info "运行所有测试并生成HTML报告"
            pytest tests/test_api_comprehensive.py -v --html=test_report.html --self-contained-html
            log_success "报告已生成: backend/test_report.html"
            ;;
        *)
            log_error "未知的测试类型: $test_type"
            echo ""
            echo "可用的测试类型:"
            echo "  all          - 运行所有测试"
            echo "  health       - 健康检查测试"
            echo "  admin        - 管理员接口测试"
            echo "  tenant       - 租户接口测试"
            echo "  conversation - 对话管理测试"
            echo "  ai           - AI对话测试"
            echo "  knowledge    - 知识库测试"
            echo "  report       - 运行所有测试并生成HTML报告"
            exit 1
            ;;
    esac

    cd ..
}

# 显示测试统计
show_stats() {
    echo ""
    log_info "测试统计:"
    echo "  总接口数: 103"
    echo "  测试用例数: 103+"
    echo "  测试类数: 15"
    echo ""
}

# 主函数
main() {
    print_banner

    # 1. 检查服务
    check_services

    # 2. 检查Python
    check_python

    # 3. 安装依赖
    install_dependencies

    # 4. 测试连通性
    test_connectivity

    # 5. 运行测试
    TEST_TYPE=${1:-all}
    run_tests $TEST_TYPE

    # 6. 显示统计
    show_stats

    log_success "测试执行完成!"
}

# 捕获中断信号
trap 'log_error "测试被中断"; exit 1' INT TERM

# 执行主函数
main "$@"

exit 0
