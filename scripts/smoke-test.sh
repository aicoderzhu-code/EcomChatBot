#!/bin/bash
###############################################################################
# 冒烟测试脚本
# 用途: 部署后验证关键功能是否正常
# 使用: bash smoke-test.sh [API_URL]
###############################################################################

set -e

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[TEST]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

###############################################################################
# 配置
###############################################################################

API_URL="${1:-http://localhost:8000}"
TIMEOUT=10
FAILED_TESTS=0
PASSED_TESTS=0
TOTAL_TESTS=0

###############################################################################
# 测试函数
###############################################################################

# 通用HTTP测试
test_endpoint() {
    local endpoint=$1
    local desc=$2
    local method=${3:-GET}
    local expected_code=${4:-200}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 [$desc]... "
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -m "$TIMEOUT" "${API_URL}${endpoint}" 2>/dev/null)
    
    if [ "$response_code" -eq "$expected_code" ]; then
        success "通过 (HTTP $response_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        fail "失败 (HTTP $response_code, 期望 $expected_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# JSON响应测试
test_json_response() {
    local endpoint=$1
    local desc=$2
    local expected_field=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 [$desc]... "
    
    local response
    response=$(curl -s -m "$TIMEOUT" "${API_URL}${endpoint}" 2>/dev/null)
    
    if echo "$response" | grep -q "$expected_field"; then
        success "通过 (包含字段: $expected_field)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        fail "失败 (未找到字段: $expected_field)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

###############################################################################
# 主测试流程
###############################################################################

log "=========================================="
log "开始冒烟测试"
log "=========================================="
log "测试目标: $API_URL"
log "超时设置: ${TIMEOUT}秒"
log "=========================================="
echo ""

# 等待服务完全启动
log "等待服务准备就绪..."
sleep 5

###############################################################################
# 1. 基础健康检查
###############################################################################

log "▶ 基础服务测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "/health" "健康检查端点"
test_json_response "/health" "健康检查JSON响应" "status"

echo ""

###############################################################################
# 2. API文档可访问性
###############################################################################

log "▶ API文档测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "/docs" "Swagger文档"
test_endpoint "/redoc" "ReDoc文档"
test_endpoint "/openapi.json" "OpenAPI Schema"

echo ""

###############################################################################
# 3. 核心业务接口
###############################################################################

log "▶ 核心业务接口测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 租户接口（405 Method Not Allowed 表示接口存在）
test_endpoint "/api/v1/tenant/register" "租户注册接口" "GET" "405"
test_endpoint "/api/v1/tenant/login" "租户登录接口" "GET" "405"

# 管理员接口
test_endpoint "/api/v1/admin/login" "管理员登录接口" "GET" "405"

# 对话接口
test_endpoint "/api/v1/conversation/create" "创建会话接口" "GET" "401"

# 知识库接口
test_endpoint "/api/v1/knowledge/list" "知识库列表接口" "GET" "401"

echo ""

###############################################################################
# 4. 性能测试（响应时间）
###############################################################################

log "▶ 性能测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "测试 [API响应时间]... "

RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" -m "$TIMEOUT" "${API_URL}/health" 2>/dev/null)
RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc)

if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
    success "通过 (${RESPONSE_MS}ms < 1000ms)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    warn "较慢 (${RESPONSE_MS}ms)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi

echo ""

###############################################################################
# 5. 容器状态检查（如果在本机）
###############################################################################

if [ "$API_URL" = "http://localhost:8000" ] || [ "$API_URL" = "http://127.0.0.1:8000" ]; then
    log "▶ 容器状态检查"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 [API容器运行状态]... "
    if docker ps | grep -q "ecom-chatbot-api"; then
        success "运行中"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        fail "未运行"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "测试 [Celery容器运行状态]... "
    if docker ps | grep -q "ecom-chatbot-celery"; then
        success "运行中"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        warn "未运行"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    echo ""
fi

###############################################################################
# 测试结果汇总
###############################################################################

log "=========================================="
log "冒烟测试完成"
log "=========================================="
echo ""
echo "📊 测试统计:"
echo "   总测试数: $TOTAL_TESTS"
echo "   通过数: $PASSED_TESTS"
echo "   失败数: $FAILED_TESTS"

if [ $FAILED_TESTS -eq 0 ]; then
    PASS_RATE=100
else
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
fi
echo "   通过率: ${PASS_RATE}%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    success "✅ 所有冒烟测试通过！"
    log "=========================================="
    exit 0
else
    fail "❌ 有 $FAILED_TESTS 个测试失败"
    log "=========================================="
    exit 1
fi
