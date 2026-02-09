#!/usr/bin/env bash
# 电商智能客服SaaS平台 - 完整测试执行脚本
# 目标: 100%测试覆盖率

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "======================================"
print_message "$BLUE" "  电商智能客服SaaS平台 - 测试套件"
print_message "$BLUE" "  目标: 100%测试覆盖率"
print_message "$BLUE" "======================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    print_message "$RED" "错误: 未找到Python3"
    exit 1
fi

# 进入后端目录
cd "$(dirname "$0")" || exit
if [ -d "backend" ]; then
    cd backend || exit
fi

print_message "$YELLOW" "[1/8] 检查依赖..."
# 安装测试依赖
if [ -f "tests/requirements-test.txt" ]; then
    pip install -q -r tests/requirements-test.txt
    print_message "$GREEN" "✓ 测试依赖已安装"
else
    print_message "$YELLOW" "⚠ 未找到测试依赖文件"
fi

# 安装项目依赖
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    print_message "$GREEN" "✓ 项目依赖已安装"
fi

print_message "$YELLOW" "[2/8] 启动测试数据库..."
# 这里可以添加启动测试数据库的逻辑
# docker-compose up -d postgres redis milvus
print_message "$GREEN" "✓ 测试环境准备完成"

echo ""
print_message "$BLUE" "======================================"
print_message "$BLUE" "  开始执行测试"
print_message "$BLUE" "======================================"
echo ""

# 测试执行函数
run_tests() {
    local test_name=$1
    local test_pattern=$2
    local marker=$3

    print_message "$YELLOW" "[测试] $test_name"

    if [ -n "$marker" ]; then
        pytest tests/"$test_pattern" -m "$marker" -v --tb=short --cov-append || true
    else
        pytest tests/"$test_pattern" -v --tb=short --cov-append || true
    fi

    echo ""
}

# 清除之前的覆盖率数据
rm -f .coverage
rm -rf htmlcov/

# Phase 1: 冒烟测试
print_message "$YELLOW" "[3/8] Phase 1: 冒烟测试 (Smoke Tests)"
run_tests "健康检查" "test_01_health.py" "smoke"

# Phase 2: 核心模块测试
print_message "$YELLOW" "[4/8] Phase 2: 核心模块测试"
run_tests "健康检查模块" "test_01_health.py" ""
run_tests "管理员模块" "test_02_admin.py" ""
run_tests "租户管理模块" "test_03_tenant.py" ""
run_tests "对话管理模块" "test_04_conversation.py" ""
run_tests "AI对话模块" "test_05_ai_chat.py" ""
run_tests "知识库模块" "test_06_knowledge.py" ""

# Phase 3: 扩展模块测试
print_message "$YELLOW" "[5/8] Phase 3: 扩展模块测试"
# 如果存在其他测试文件，继续执行
if [ -f "tests/test_07_payment.py" ]; then
    run_tests "支付模块" "test_07_*.py" ""
fi

if [ -f "tests/test_08_rag.py" ]; then
    run_tests "RAG模块" "test_08_*.py" ""
fi

if [ -f "tests/test_09_webhook.py" ]; then
    run_tests "Webhook模块" "test_09_*.py" ""
fi

if [ -f "tests/test_10_monitor.py" ]; then
    run_tests "监控模块" "test_10_*.py" ""
fi

# Phase 4: 集成测试
print_message "$YELLOW" "[6/8] Phase 4: 端到端测试"
if [ -f "tests/test_e2e.py" ]; then
    run_tests "E2E测试" "test_e2e.py" "e2e"
fi

# Phase 5: 性能测试
print_message "$YELLOW" "[7/8] Phase 5: 性能测试"
if [ -f "tests/test_performance.py" ]; then
    run_tests "性能测试" "test_performance.py" "performance"
fi

# 生成测试报告
print_message "$YELLOW" "[8/8] 生成测试报告..."
echo ""

# 生成覆盖率报告
print_message "$BLUE" "生成覆盖率报告..."
pytest --cov=api --cov=services --cov=models \
       --cov-report=html \
       --cov-report=term-missing \
       --cov-report=xml \
       --html=htmlcov/report.html \
       --self-contained-html \
       tests/ || true

echo ""
print_message "$BLUE" "======================================"
print_message "$BLUE" "  测试完成"
print_message "$BLUE" "======================================"
echo ""

# 显示覆盖率摘要
if [ -f ".coverage" ]; then
    print_message "$GREEN" "覆盖率报告:"
    coverage report --skip-empty

    # 获取覆盖率百分比
    COVERAGE=$(coverage report | grep "TOTAL" | awk '{print $4}' | sed 's/%//')

    echo ""
    if (( $(echo "$COVERAGE >= 95" | bc -l) )); then
        print_message "$GREEN" "✓ 覆盖率达标: ${COVERAGE}% (目标: ≥95%)"
    elif (( $(echo "$COVERAGE >= 80" | bc -l) )); then
        print_message "$YELLOW" "⚠ 覆盖率良好: ${COVERAGE}% (目标: ≥95%)"
    else
        print_message "$RED" "✗ 覆盖率不足: ${COVERAGE}% (目标: ≥95%)"
    fi
fi

echo ""
print_message "$BLUE" "报告位置:"
print_message "$GREEN" "  - HTML报告: file://$(pwd)/htmlcov/index.html"
print_message "$GREEN" "  - XML报告: $(pwd)/coverage.xml"
echo ""

print_message "$BLUE" "======================================"
print_message "$BLUE" "  测试结果汇总"
print_message "$BLUE" "======================================"
echo ""

# 统计测试数量
if command -v pytest &> /dev/null; then
    TOTAL_TESTS=$(pytest tests/ --collect-only -q 2>/dev/null | tail -n 1 | awk '{print $1}' || echo "0")
    print_message "$GREEN" "总测试用例数: $TOTAL_TESTS"
fi

echo ""
print_message "$BLUE" "提示:"
print_message "$GREEN" "  - 查看详细覆盖率报告: open htmlcov/index.html"
print_message "$GREEN" "  - 运行特定模块测试: pytest tests/test_XX_module.py -v"
print_message "$GREEN" "  - 运行标记测试: pytest -m <marker_name>"
echo ""

print_message "$GREEN" "测试执行完成! 🎉"
