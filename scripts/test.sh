#!/bin/bash

##############################################
# 电商智能客服 SaaS 平台 - 快速测试脚本
# 测试部署是否成功
##############################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║         电商智能客服 SaaS 平台 - 快速测试              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 1. 测试 API 健康
log_info "测试 API 健康状态..."
if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
    log_success "✓ API 服务正常"
else
    log_error "✗ API 服务不可访问"
    exit 1
fi

# 2. 测试管理员登录
log_info "测试管理员登录..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    log_success "✓ 管理员登录成功"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
else
    log_error "✗ 管理员登录失败"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# 3. 测试租户注册（替代管理员信息测试）
log_info "测试租户注册..."
TIMESTAMP=$(date +%s)
REGISTER_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/tenant/register" \
    -H "Content-Type: application/json" \
    -d "{\"company_name\":\"测试公司\",\"contact_name\":\"测试\",\"contact_email\":\"test_${TIMESTAMP}@example.com\",\"password\":\"test123\"}")

if echo "$REGISTER_RESPONSE" | grep -q "tenant_id"; then
    log_success "✓ 租户注册成功"
    API_KEY=$(echo "$REGISTER_RESPONSE" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
else
    log_error "✗ 租户注册失败"
    echo "$REGISTER_RESPONSE"
    exit 1
fi

# 4. 测试API Key认证
log_info "测试API Key认证..."
TENANT_INFO=$(curl -s -X GET "http://localhost:8000/api/v1/tenant/info" \
    -H "X-API-Key: $API_KEY")

if echo "$TENANT_INFO" | grep -q "tenant_id"; then
    log_success "✓ API Key认证成功"
else
    log_error "✗ API Key认证失败"
    exit 1
fi

# 5. 测试数据库连接
log_info "测试数据库连接..."
if docker-compose exec -T postgres psql -U ecom_user -d ecom_chatbot -c "SELECT 1" > /dev/null 2>&1; then
    log_success "✓ 数据库连接正常"
else
    log_error "✗ 数据库连接失败"
    exit 1
fi

# 6. 测试 Redis 连接
log_info "测试 Redis 连接..."
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    log_success "✓ Redis 连接正常"
else
    log_error "✗ Redis 连接失败"
    exit 1
fi

echo ""
log_success "🎉 所有测试通过！部署成功！"
echo ""
log_info "您可以开始使用以下服务："
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo "  - 租户注册示例: curl -X POST http://localhost:8000/api/v1/tenant/register -H 'Content-Type: application/json' -d '{\"company_name\":\"测试\",\"contact_name\":\"张三\",\"contact_email\":\"test@example.com\",\"password\":\"test123\"}'"
echo ""
