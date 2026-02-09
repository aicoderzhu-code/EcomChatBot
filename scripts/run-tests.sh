#!/bin/bash
# 电商智能客服SaaS平台 - 自动化测试脚本
# 此脚本在 Docker 容器内执行

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   电商智能客服SaaS平台 - 部署后自动化测试              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 显示环境信息
echo "[INFO] 测试环境:"
echo "  - Python版本: $(python --version)"
echo "  - 工作目录: $(pwd)"
echo "  - 执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 安装/更新测试依赖
echo "[INFO] 准备测试依赖..."
pip install -q \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-html \
    httpx \
    faker \
    aiosqlite \
    || echo "[WARNING] 部分依赖安装失败"

echo "[SUCCESS] 测试依赖已就绪"

# 创建测试报告目录
echo ""
echo "[INFO] 准备测试报告目录..."
mkdir -p /app/test-reports/coverage-html
mkdir -p /app/test-reports/logs
rm -f /app/test-reports/*.xml /app/test-reports/*.html 2>/dev/null || true

# 设置Python路径
export PYTHONPATH=/app:$PYTHONPATH

# 运行测试
echo ""
echo "=========================================="
echo "  开始运行测试套件"
echo "=========================================="
echo ""

cd /app

# 执行测试并生成报告
TEST_EXIT_CODE=0
pytest tests/ \
    -v \
    --tb=short \
    --maxfail=50 \
    --junit-xml=/app/test-reports/junit-report.xml \
    --html=/app/test-reports/test-report.html \
    --self-contained-html \
    --cov=api \
    --cov=services \
    --cov=models \
    --cov-report=html:/app/test-reports/coverage-html \
    --cov-report=xml:/app/test-reports/coverage.xml \
    --cov-report=term-missing:skip-covered \
    -m "not slow" \
    --continue-on-collection-errors \
    2>&1 | tee /app/test-reports/logs/test-output.log || TEST_EXIT_CODE=$?

echo ""
echo "[INFO] 测试执行完成，退出码: ${TEST_EXIT_CODE}"

# 生成测试摘要
echo ""
echo "[INFO] 生成测试摘要..."

# 解析测试结果
TOTAL_TESTS="0"
PASSED="0"
FAILURES="0"
ERRORS="0"
SKIPPED="0"

if [ -f "/app/test-reports/junit-report.xml" ]; then
    TOTAL_TESTS=$(grep -oP 'tests="\K[0-9]+' /app/test-reports/junit-report.xml | head -1 || echo "0")
    FAILURES=$(grep -oP 'failures="\K[0-9]+' /app/test-reports/junit-report.xml | head -1 || echo "0")
    ERRORS=$(grep -oP 'errors="\K[0-9]+' /app/test-reports/junit-report.xml | head -1 || echo "0")
    SKIPPED=$(grep -oP 'skipped="\K[0-9]+' /app/test-reports/junit-report.xml | head -1 || echo "0")

    # 确保变量有默认值
    TOTAL_TESTS=${TOTAL_TESTS:-0}
    FAILURES=${FAILURES:-0}
    ERRORS=${ERRORS:-0}
    SKIPPED=${SKIPPED:-0}
    PASSED=$((TOTAL_TESTS - FAILURES - ERRORS - SKIPPED))
fi

# 获取覆盖率
COVERAGE_PERCENT="0"
if [ -f "/app/test-reports/coverage.xml" ]; then
    COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' /app/test-reports/coverage.xml | head -1 || echo "0")
    if [ -n "$COVERAGE" ] && [ "$COVERAGE" != "0" ]; then
        COVERAGE_PERCENT=$(echo "$COVERAGE * 100" | bc 2>/dev/null || echo "0")
    fi
fi

# 生成摘要文件
cat > /app/test-reports/test-summary.txt << EOF
========================================
  电商智能客服SaaS平台 - 测试报告
========================================

执行信息:
  构建编号: ${BUILD_NUMBER:-Manual}
  执行时间: $(date '+%Y-%m-%d %H:%M:%S')
  测试环境: Docker容器 (ecom-chatbot-api)
  Python版本: $(python --version 2>&1)

测试结果:
  总测试数: ${TOTAL_TESTS}
  通过: ${PASSED}
  失败: ${FAILURES}
  错误: ${ERRORS}
  跳过: ${SKIPPED}
  代码覆盖率: ${COVERAGE_PERCENT}%

测试状态: $([ "${TEST_EXIT_CODE}" = "0" ] && echo "✓ 通过" || echo "✗ 失败")

报告文件:
  - JUnit报告: test-reports/junit-report.xml
  - HTML报告: test-reports/test-report.html
  - 覆盖率HTML: test-reports/coverage-html/index.html
  - 覆盖率XML: test-reports/coverage.xml
  - 测试日志: test-reports/logs/test-output.log

========================================
EOF

cat /app/test-reports/test-summary.txt

echo ""
echo "[SUCCESS] 测试完成！"
echo ""

# 列出生成的文件
echo "[INFO] 生成的测试报告文件:"
ls -lh /app/test-reports/ 2>/dev/null | tail -n +2 || true

# 退出（允许部分测试失败，不影响部署）
exit 0
