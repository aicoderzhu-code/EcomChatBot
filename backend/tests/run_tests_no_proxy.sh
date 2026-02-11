#!/bin/bash
# 无代理测试执行脚本

set -e

echo "==========================================\n🧪 电商智能客服系统 - 完整测试执行\n=========================================="
echo ""

# 禁用所有代理
unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY
unset all_proxy
unset ALL_PROXY
unset no_proxy
unset NO_PROXY

# 设置Python环境变量禁用代理
export PYTHONNOPROXY="*"
export NO_PROXY="*"

echo "✅ 已禁用所有代理设置"
echo ""

# 切换到测试目录
cd "$(dirname "$0")"

# 激活conda环境
source /Users/zhulang/miniconda3/etc/profile.d/conda.sh
conda activate ecom-chat-bot

echo "✅ Conda环境已激活: ecom-chat-bot"
echo ""

# 测试连接
echo "🔍 测试API连接..."
if curl -s --noproxy "*" http://127.0.0.1:8000/api/v1/health > /dev/null; then
    echo "✅ API连接正常"
else
    echo "❌ 无法连接到API服务"
    exit 1
fi
echo ""

# 执行测试
echo "🚀 开始执行完整测试套件..."
echo "=========================================="
echo ""

pytest -v --tb=short "$@"

echo ""
echo "=========================================="
echo "✅ 测试执行完成"
echo "=========================================="
