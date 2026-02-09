#!/usr/bin/env bash
###############################################################################
# CI/CD测试集成 - 验证脚本
# 用途: 快速验证所有文件和配置是否正确
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/opt/projects/ecom-chat-bot"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  CI/CD测试集成 - 验证脚本                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

check_item() {
    local desc=$1
    local check_cmd=$2
    
    echo -n "检查 $desc ... "
    
    if eval "$check_cmd" &>/dev/null; then
        echo -e "${GREEN}✓ 通过${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 文件完整性检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_item "Jenkinsfile存在" \
    "test -f $PROJECT_DIR/Jenkinsfile"

check_item "Jenkinsfile包含测试阶段" \
    "grep -q '运行自动化测试' $PROJECT_DIR/Jenkinsfile"

check_item "CI测试脚本存在" \
    "test -f $PROJECT_DIR/backend/tests/run_ci_tests.sh"

check_item "CI测试脚本可执行" \
    "test -x $PROJECT_DIR/backend/tests/run_ci_tests.sh"

check_item "CI/CD测试指南存在" \
    "test -f $PROJECT_DIR/CI_CD_TESTING_GUIDE.md"

check_item "Jenkins快速参考存在" \
    "test -f $PROJECT_DIR/JENKINS_SETUP_QUICK_REFERENCE.md"

check_item "完成总结文档存在" \
    "test -f $PROJECT_DIR/CI_CD_COMPLETION_SUMMARY.md"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  2. 测试套件检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_item "测试目录存在" \
    "test -d $PROJECT_DIR/backend/tests"

check_item "测试配置文件存在" \
    "test -f $PROJECT_DIR/backend/tests/pytest.ini"

check_item "测试依赖文件存在" \
    "test -f $PROJECT_DIR/backend/tests/requirements-test.txt"

check_item "测试工具文件存在" \
    "test -f $PROJECT_DIR/backend/tests/test_utils.py"

check_item "conftest.py存在" \
    "test -f $PROJECT_DIR/backend/tests/conftest.py"

# 统计测试文件数量
TEST_FILE_COUNT=$(find $PROJECT_DIR/backend/tests -name "test_*.py" -type f | wc -l)
if [ "$TEST_FILE_COUNT" -ge 10 ]; then
    echo -e "检查 测试文件数量 (${TEST_FILE_COUNT}个) ... ${GREEN}✓ 通过${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "检查 测试文件数量 (${TEST_FILE_COUNT}个) ... ${RED}✗ 失败${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  3. Python环境检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_item "Python3可用" \
    "command -v python3"

check_item "pip3可用" \
    "command -v pip3"

if python3 -c "import pytest" 2>/dev/null; then
    echo -e "检查 pytest已安装 ... ${GREEN}✓ 通过${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "检查 pytest已安装 ... ${YELLOW}⚠ 未安装 (可选)${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4. Jenkinsfile配置检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_item "包含JUnit报告发布" \
    "grep -q 'junit.*junit-report.xml' $PROJECT_DIR/Jenkinsfile"

check_item "包含HTML报告发布" \
    "grep -q 'publishHTML' $PROJECT_DIR/Jenkinsfile"

check_item "包含报告归档" \
    "grep -q 'archiveArtifacts' $PROJECT_DIR/Jenkinsfile"

check_item "包含post配置" \
    "grep -q 'post {' $PROJECT_DIR/Jenkinsfile"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  5. Docker环境检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_item "Docker可用" \
    "command -v docker"

check_item "docker-compose配置存在" \
    "test -f $PROJECT_DIR/docker-compose.yml"

if docker-compose -f $PROJECT_DIR/docker-compose.yml ps | grep -q "Up"; then
    echo -e "检查 Docker服务运行中 ... ${GREEN}✓ 通过${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "检查 Docker服务运行中 ... ${YELLOW}⚠ 未运行 (可选)${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  验证结果"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_COUNT=$((SUCCESS_COUNT + FAIL_COUNT))

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！ ($SUCCESS_COUNT/$TOTAL_COUNT)${NC}"
    echo ""
    echo "🎉 CI/CD测试集成配置正确！"
    echo ""
    echo "下一步:"
    echo "  1. 在Jenkins中创建Pipeline项目"
    echo "  2. 连接Gitee仓库"
    echo "  3. 指定Jenkinsfile路径"
    echo "  4. 触发首次构建"
    echo ""
    echo "📚 查看文档:"
    echo "  cat $PROJECT_DIR/JENKINS_SETUP_QUICK_REFERENCE.md"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠ 部分检查未通过 (✓$SUCCESS_COUNT ✗$FAIL_COUNT)${NC}"
    echo ""
    echo "请检查失败项并修复"
    echo ""
    exit 1
fi
