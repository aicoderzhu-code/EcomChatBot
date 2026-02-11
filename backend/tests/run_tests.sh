#!/bin/bash
# 测试执行脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🧪 电商智能客服系统 - 本地测试执行"
echo "=========================================="
echo ""

# 切换到测试目录
cd "$(dirname "$0")"

# 检查环境文件
if [ ! -f ".env.test" ]; then
    echo "❌ 错误: 未找到 .env.test 文件"
    echo "请先配置 .env.test 文件（参考 .env.test.example）"
    exit 1
fi

echo "✅ 环境配置文件已找到"
echo ""

# 检查Python版本
echo "🔍 检查 Python 版本..."
python3 --version || {
    echo "❌ 错误: 未找到 Python3"
    exit 1
}
echo ""

# 检查依赖
echo "🔍 检查测试依赖..."
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "⚠️  未安装 pytest，正在安装依赖..."
    pip3 install pytest pytest-asyncio httpx python-dotenv pydantic pydantic-settings
else
    echo "✅ 测试依赖已安装"
fi
echo ""

# 检查服务器连接
echo "🔍 检查服务器连接..."
BASE_URL=$(grep "^BASE_URL=" .env.test | cut -d '=' -f2)
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" | grep -q "200\|404"; then
    echo "✅ 服务器连接正常: $BASE_URL"
else
    echo "⚠️  警告: 无法连接到服务器: $BASE_URL"
    echo "请确认服务器是否正在运行"
    read -p "是否继续测试? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# 显示测试选项
echo "=========================================="
echo "📋 可用的测试套件:"
echo "=========================================="
echo "1. 完整测试（所有测试）"
echo "2. 基础 API 测试（不含性能和安全）"
echo "3. 集成测试"
echo "4. 健康检查测试（快速验证）"
echo "5. 租户管理测试"
echo "6. 对话和 AI 测试"
echo "7. 知识库和 RAG 测试"
echo "8. 性能测试"
echo "9. 安全测试"
echo "0. 自定义命令"
echo ""

read -p "请选择测试套件 (1-9, 0=自定义): " choice
echo ""

case $choice in
    1)
        echo "🚀 执行完整测试..."
        pytest -v --tb=short
        ;;
    2)
        echo "🚀 执行基础 API 测试..."
        pytest api/ -v --tb=short -m "not performance and not security"
        ;;
    3)
        echo "🚀 执行集成测试..."
        pytest integration/ -v --tb=short
        ;;
    4)
        echo "🚀 执行健康检查测试..."
        pytest api/test_health.py -v --tb=short
        ;;
    5)
        echo "🚀 执行租户管理测试..."
        pytest api/test_tenant.py api/test_auth.py -v --tb=short
        ;;
    6)
        echo "🚀 执行对话和 AI 测试..."
        pytest api/test_conversation.py api/test_ai_chat.py -v --tb=short
        ;;
    7)
        echo "🚀 执行知识库和 RAG 测试..."
        pytest api/test_knowledge.py api/test_rag.py -v --tb=short
        ;;
    8)
        echo "🚀 执行性能测试..."
        pytest performance/ -v --tb=short
        ;;
    9)
        echo "🚀 执行安全测试..."
        pytest security/ -v --tb=short
        ;;
    0)
        read -p "请输入 pytest 命令（例如: pytest api/ -k tenant）: " custom_cmd
        eval "$custom_cmd"
        ;;
    *)
        echo "❌ 无效的选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ 测试执行完成"
echo "=========================================="
