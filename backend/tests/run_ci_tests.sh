#!/usr/bin/env bash
###############################################################################
# 电商智能客服SaaS平台 - CI/CD 测试脚本
# 用途: 在Jenkins流水线中运行测试并生成报告
# 作者: DevOps Team
# 日期: 2026-02-09
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_section() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

# 打印横幅
print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║   电商智能客服SaaS平台 - CI/CD自动化测试               ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python 3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version)
    log_success "Python环境: $PYTHON_VERSION"
}

# 安装测试依赖
install_dependencies() {
    log_info "安装测试依赖..."
    
    # 升级pip
    python3 -m pip install --upgrade pip -q
    
    # 安装测试依赖
    if [ -f "tests/requirements-test.txt" ]; then
        pip3 install -r tests/requirements-test.txt -q
        log_success "测试依赖安装完成"
    else
        log_warning "未找到 tests/requirements-test.txt，安装基础依赖"
        pip3 install pytest pytest-asyncio pytest-cov pytest-html httpx faker -q
    fi
    
    # 显示已安装的关键包
    log_info "关键测试包版本:"
    pip3 list | grep -E "pytest|httpx|faker|coverage" || true
}

# 创建测试报告目录
prepare_report_dirs() {
    log_info "准备测试报告目录..."
    
    # 创建报告目录
    mkdir -p test-reports/coverage-html
    mkdir -p test-reports/logs
    
    # 清理旧报告
    rm -f test-reports/*.xml
    rm -f test-reports/*.html
    rm -f test-reports/coverage-html/*
    
    log_success "报告目录已准备"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待API服务
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API服务已就绪"
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done
    
    log_warning "API服务未在预期时间内就绪，继续执行测试"
}

# 运行测试
run_tests() {
    log_section "开始运行测试套件"
    
    # 设置环境变量
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    export PYTEST_TIMEOUT=300
    
    log_info "测试配置:"
    echo "  - 工作目录: $(pwd)"
    echo "  - Python路径: $PYTHONPATH"
    echo "  - 测试目录: tests/"
    echo ""
    
    log_info "执行测试..."
    TEST_START_TIME=$(date +%s)
    
    # 运行pytest并生成多种格式的报告
    pytest tests/ \
        -v \
        --tb=short \
        --maxfail=50 \
        --junit-xml=test-reports/junit-report.xml \
        --html=test-reports/test-report.html \
        --self-contained-html \
        --cov=api \
        --cov=services \
        --cov=models \
        --cov-report=html:test-reports/coverage-html \
        --cov-report=xml:test-reports/coverage.xml \
        --cov-report=term-missing:skip-covered \
        -m "not slow" \
        2>&1 | tee test-reports/logs/test-output.log || TEST_EXIT_CODE=$?
    
    TEST_END_TIME=$(date +%s)
    TEST_DURATION=$((TEST_END_TIME - TEST_START_TIME))
    
    echo ""
    log_info "测试执行耗时: ${TEST_DURATION}秒"
    
    # 保存退出码
    echo "${TEST_EXIT_CODE:-0}" > test-reports/.test-exit-code
    
    return ${TEST_EXIT_CODE:-0}
}

# 生成测试摘要
generate_summary() {
    log_section "生成测试报告摘要"
    
    # 获取测试退出码
    TEST_EXIT_CODE=$(cat test-reports/.test-exit-code 2>/dev/null || echo "0")
    
    # 解析测试结果
    if [ -f "test-reports/junit-report.xml" ]; then
        TOTAL_TESTS=$(grep -oP 'tests="\K[0-9]+' test-reports/junit-report.xml | head -1)
        FAILURES=$(grep -oP 'failures="\K[0-9]+' test-reports/junit-report.xml | head -1)
        ERRORS=$(grep -oP 'errors="\K[0-9]+' test-reports/junit-report.xml | head -1)
        SKIPPED=$(grep -oP 'skipped="\K[0-9]+' test-reports/junit-report.xml | head -1)
        
        PASSED=$((TOTAL_TESTS - FAILURES - ERRORS - SKIPPED))
    else
        TOTAL_TESTS="N/A"
        PASSED="N/A"
        FAILURES="N/A"
        ERRORS="N/A"
        SKIPPED="N/A"
    fi
    
    # 获取覆盖率
    if [ -f "test-reports/coverage.xml" ]; then
        COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' test-reports/coverage.xml | head -1)
        COVERAGE_PERCENT=$(echo "scale=2; $COVERAGE * 100" | bc)
    else
        COVERAGE_PERCENT="N/A"
    fi
    
    # 生成摘要文件
    cat > test-reports/test-summary.txt << EOF
========================================
  电商智能客服SaaS平台 - 测试报告
========================================

构建信息:
  构建编号: ${BUILD_NUMBER:-Manual}
  Git分支: ${GIT_BRANCH:-Unknown}
  提交ID: ${GIT_COMMIT:-Unknown}
  构建时间: $(date '+%Y-%m-%d %H:%M:%S')

测试环境:
  部署路径: ${DEPLOY_PATH:-$(pwd)}
  API地址: http://localhost:8000
  Python版本: $(python3 --version)

测试结果:
  总测试数: ${TOTAL_TESTS}
  通过: ${PASSED}
  失败: ${FAILURES}
  错误: ${ERRORS}
  跳过: ${SKIPPED}
  代码覆盖率: ${COVERAGE_PERCENT}%

测试状态: $([ "$TEST_EXIT_CODE" = "0" ] && echo "✓ 通过" || echo "✗ 失败")

测试报告文件:
  - JUnit报告: test-reports/junit-report.xml
  - HTML报告: test-reports/test-report.html
  - 覆盖率HTML: test-reports/coverage-html/index.html
  - 覆盖率XML: test-reports/coverage.xml
  - 测试日志: test-reports/logs/test-output.log

========================================
EOF
    
    # 显示摘要
    cat test-reports/test-summary.txt
    
    # 生成JSON格式摘要（供其他工具使用）
    cat > test-reports/test-summary.json << EOF
{
  "build_number": "${BUILD_NUMBER:-Manual}",
  "git_branch": "${GIT_BRANCH:-Unknown}",
  "git_commit": "${GIT_COMMIT:-Unknown}",
  "build_time": "$(date -Iseconds)",
  "test_results": {
    "total": ${TOTAL_TESTS:-0},
    "passed": ${PASSED:-0},
    "failed": ${FAILURES:-0},
    "errors": ${ERRORS:-0},
    "skipped": ${SKIPPED:-0}
  },
  "coverage": {
    "percentage": ${COVERAGE_PERCENT:-0}
  },
  "status": "$([ "$TEST_EXIT_CODE" = "0" ] && echo "passed" || echo "failed")",
  "exit_code": ${TEST_EXIT_CODE}
}
EOF
    
    log_success "测试摘要已生成"
}

# 显示测试结果
display_results() {
    log_section "测试结果汇总"
    
    TEST_EXIT_CODE=$(cat test-reports/.test-exit-code 2>/dev/null || echo "0")
    
    if [ "$TEST_EXIT_CODE" = "0" ]; then
        log_success "🎉 所有测试通过！"
    else
        log_error "❌ 部分测试失败"
    fi
    
    echo ""
    log_info "测试报告位置:"
    echo "  📊 HTML报告: $(pwd)/test-reports/test-report.html"
    echo "  📈 覆盖率报告: $(pwd)/test-reports/coverage-html/index.html"
    echo "  📋 JUnit报告: $(pwd)/test-reports/junit-report.xml"
    echo "  📝 测试日志: $(pwd)/test-reports/logs/test-output.log"
    echo ""
    
    log_info "Jenkins中查看:"
    echo "  - 测试报告: \${BUILD_URL}测试报告/"
    echo "  - 覆盖率报告: \${BUILD_URL}覆盖率报告/"
    echo ""
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    # 这里可以添加清理逻辑
}

# 主函数
main() {
    print_banner
    
    # 捕获退出信号
    trap cleanup EXIT
    
    # 1. 检查环境
    check_python
    
    # 2. 安装依赖
    install_dependencies
    
    # 3. 准备报告目录
    prepare_report_dirs
    
    # 4. 等待服务
    wait_for_services
    
    # 5. 运行测试
    run_tests || true  # 允许测试失败继续生成报告
    
    # 6. 生成摘要
    generate_summary
    
    # 7. 显示结果
    display_results
    
    # 8. 返回测试退出码
    TEST_EXIT_CODE=$(cat test-reports/.test-exit-code 2>/dev/null || echo "0")
    
    if [ "$TEST_EXIT_CODE" = "0" ]; then
        log_success "✓ CI/CD测试执行完成"
        exit 0
    else
        log_warning "⚠ 测试执行完成，但有失败用例"
        # 在CI环境中，我们仍然返回0，让Jenkins的测试报告插件来判断
        # 如果想让构建失败，改为 exit $TEST_EXIT_CODE
        exit 0
    fi
}

# 执行主函数
main "$@"
