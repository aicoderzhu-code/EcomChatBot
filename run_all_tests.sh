#!/bin/bash
#
# 前后端完整测试运行脚本
#
# 功能:
#   1. 执行后端所有 API / 集成 / 性能 / 安全测试
#   2. 执行前端 Playwright E2E 测试
#   3. 测试完成后清理所有测试数据
#   4. 合并生成统一 HTML 测试报告
#
# 用法:
#   ./run_all_tests.sh              # 运行所有测试
#   ./run_all_tests.sh --backend    # 仅后端
#   ./run_all_tests.sh --frontend   # 仅前端
#   ./run_all_tests.sh --fast       # 快速模式(跳过慢速测试)
#

set -e

# ==================== 配置 ====================
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
TESTS_DIR="$BACKEND_DIR/tests"
REPORT_DIR="$PROJECT_ROOT/test-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认运行全部
RUN_BACKEND=true
RUN_FRONTEND=true
FAST_MODE=false
BACKEND_EXIT=0
FRONTEND_EXIT=0

# ==================== 参数解析 ====================
for arg in "$@"; do
    case $arg in
        --backend)
            RUN_FRONTEND=false
            ;;
        --frontend)
            RUN_BACKEND=false
            ;;
        --fast)
            FAST_MODE=true
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --backend    仅运行后端测试"
            echo "  --frontend   仅运行前端测试"
            echo "  --fast       快速模式(跳过慢速/性能/支付测试)"
            echo "  --help       显示帮助信息"
            exit 0
            ;;
    esac
done

# ==================== 准备 ====================
echo -e "${CYAN}"
echo "============================================================"
echo "  电商智能客服系统 - 完整测试套件"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo -e "${NC}"

mkdir -p "$REPORT_DIR"

# ==================== 后端测试 ====================
if [ "$RUN_BACKEND" = true ]; then
    echo -e "\n${BLUE}[1/3] 运行后端测试...${NC}\n"

    cd "$TESTS_DIR"

    # 确保有 .env.test
    if [ ! -f ".env.test" ] && [ -f ".env.test.example" ]; then
        cp .env.test.example .env.test
        echo -e "${YELLOW}  已从模板创建 .env.test${NC}"
    fi

    # 构建 pytest 命令
    PYTEST_ARGS="-v --strict-markers --tb=short"
    PYTEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/backend_report_${TIMESTAMP}.html --self-contained-html"
    PYTEST_ARGS="$PYTEST_ARGS --junitxml=$REPORT_DIR/backend_junit_${TIMESTAMP}.xml"

    if [ "$FAST_MODE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS -m 'not slow and not performance and not payment'"
        PYTEST_ARGS="$PYTEST_ARGS --timeout=60"
        echo -e "${YELLOW}  快速模式: 跳过慢速/性能/支付测试${NC}"
    else
        PYTEST_ARGS="$PYTEST_ARGS --timeout=120"
    fi

    # 强制清理测试数据
    export CLEANUP_AFTER_TEST=true

    echo -e "${CYAN}  pytest $PYTEST_ARGS${NC}\n"

    set +e
    python -m pytest $PYTEST_ARGS 2>&1 | tee "$REPORT_DIR/backend_output_${TIMESTAMP}.log"
    BACKEND_EXIT=${PIPESTATUS[0]}
    set -e

    if [ $BACKEND_EXIT -eq 0 ]; then
        echo -e "\n${GREEN}  ✓ 后端测试全部通过${NC}"
    else
        echo -e "\n${RED}  ✗ 后端测试存在失败 (退出码: $BACKEND_EXIT)${NC}"
    fi

    cd "$PROJECT_ROOT"
fi

# ==================== 前端 E2E 测试 ====================
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "\n${BLUE}[2/3] 运行前端 E2E 测试...${NC}\n"

    cd "$FRONTEND_DIR"

    # 检查 Playwright 是否安装
    if ! npx playwright --version &> /dev/null; then
        echo -e "${YELLOW}  安装 Playwright 浏览器...${NC}"
        npx playwright install chromium
    fi

    set +e
    npx playwright test \
        --reporter=html \
        --output="$REPORT_DIR/frontend_traces" \
        2>&1 | tee "$REPORT_DIR/frontend_output_${TIMESTAMP}.log"
    FRONTEND_EXIT=${PIPESTATUS[0]}
    set -e

    # 复制 Playwright 报告
    if [ -d "e2e-report" ]; then
        cp -r e2e-report "$REPORT_DIR/frontend_report_${TIMESTAMP}"
    fi

    if [ $FRONTEND_EXIT -eq 0 ]; then
        echo -e "\n${GREEN}  ✓ 前端 E2E 测试全部通过${NC}"
    else
        echo -e "\n${RED}  ✗ 前端 E2E 测试存在失败 (退出码: $FRONTEND_EXIT)${NC}"
    fi

    cd "$PROJECT_ROOT"
fi

# ==================== 生成汇总报告 ====================
echo -e "\n${BLUE}[3/3] 生成汇总测试报告...${NC}\n"

SUMMARY_FILE="$REPORT_DIR/summary_${TIMESTAMP}.html"

cat > "$SUMMARY_FILE" << 'HEADER'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>测试报告汇总</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 20px; }
  .container { max-width: 1000px; margin: 0 auto; }
  .header { background: linear-gradient(135deg, #1890ff, #722ed1); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }
  .header h1 { font-size: 24px; margin-bottom: 8px; }
  .header p { opacity: 0.9; font-size: 14px; }
  .section { background: white; border-radius: 8px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .section h2 { font-size: 18px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #f0f0f0; }
  .status { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 13px; font-weight: 600; }
  .pass { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
  .fail { background: #fff2f0; color: #ff4d4f; border: 1px solid #ffa39e; }
  .skip { background: #fffbe6; color: #faad14; border: 1px solid #ffe58f; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #f0f0f0; }
  th { background: #fafafa; font-weight: 600; font-size: 13px; color: #666; }
  td { font-size: 14px; }
  .report-links a { display: inline-block; margin: 4px 8px 4px 0; padding: 6px 14px; background: #1890ff; color: white; text-decoration: none; border-radius: 4px; font-size: 13px; }
  .report-links a:hover { background: #40a9ff; }
  .footer { text-align: center; padding: 20px; color: #999; font-size: 13px; }
</style>
</head>
<body>
<div class="container">
HEADER

cat >> "$SUMMARY_FILE" << EOF
<div class="header">
  <h1>电商智能客服 - 测试报告汇总</h1>
  <p>生成时间: $(date '+%Y-%m-%d %H:%M:%S') | 运行ID: ${TIMESTAMP}</p>
</div>

<div class="section">
  <h2>测试结果概览</h2>
  <table>
    <tr>
      <th>测试套件</th>
      <th>状态</th>
      <th>详情</th>
    </tr>
EOF

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_EXIT -eq 0 ]; then
        echo '<tr><td>后端 API / 集成 / 安全测试</td><td><span class="status pass">通过</span></td><td>所有测试用例通过</td></tr>' >> "$SUMMARY_FILE"
    else
        echo '<tr><td>后端 API / 集成 / 安全测试</td><td><span class="status fail">失败</span></td><td>部分测试用例失败，请查看详细报告</td></tr>' >> "$SUMMARY_FILE"
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_EXIT -eq 0 ]; then
        echo '<tr><td>前端 E2E 测试 (Playwright)</td><td><span class="status pass">通过</span></td><td>所有页面流程测试通过</td></tr>' >> "$SUMMARY_FILE"
    else
        echo '<tr><td>前端 E2E 测试 (Playwright)</td><td><span class="status fail">失败</span></td><td>部分E2E测试失败，请查看详细报告</td></tr>' >> "$SUMMARY_FILE"
    fi
fi

cat >> "$SUMMARY_FILE" << EOF
  </table>
</div>

<div class="section">
  <h2>测试覆盖范围</h2>
  <table>
    <tr><th>模块</th><th>测试文件</th><th>覆盖接口</th></tr>
    <tr><td>认证授权</td><td>test_auth.py</td><td>API Key / JWT / 跨租户防护</td></tr>
    <tr><td>租户管理</td><td>test_tenant.py</td><td>注册 / 登录 / 信息查询 / 订阅 / 配额</td></tr>
    <tr><td>对话管理</td><td>test_conversation.py</td><td>创建 / 列表 / 消息 / 关闭 / 评价</td></tr>
    <tr><td>AI 对话</td><td>test_ai_chat.py</td><td>基础对话 / RAG对话 / 意图 / 摘要 / 多轮</td></tr>
    <tr><td>知识库</td><td>test_knowledge.py</td><td>CRUD / 批量导入 / 搜索 / 分类</td></tr>
    <tr><td>RAG 检索</td><td>test_rag.py</td><td>检索 / 生成 / 索引 / 统计</td></tr>
    <tr><td>意图识别</td><td>test_intent.py</td><td>分类 / 实体提取 / 类型列表</td></tr>
    <tr><td>监控统计</td><td>test_monitor.py</td><td>对话统计 / 响应时间 / 满意度 / Dashboard</td></tr>
    <tr><td>数据分析</td><td>test_analytics.py</td><td>对话分析 / 增长分析</td></tr>
    <tr><td>质量评估</td><td>test_quality.py</td><td>对话质量 / 质量汇总</td></tr>
    <tr><td>模型配置</td><td>test_model_config.py</td><td>CRUD / 默认模型 / 多提供商</td></tr>
    <tr><td>管理员</td><td>test_admin.py</td><td>登录 / 租户管理 / 审计</td></tr>
    <tr><td>支付管理</td><td>test_payment.py</td><td>订单 / 退款 / 订阅 / 回调 / 差价预览</td></tr>
    <tr><td>Webhook</td><td>test_webhook.py</td><td>CRUD / 日志 / 测试发送 / 跨租户防护</td></tr>
    <tr><td>审计日志</td><td>test_audit.py</td><td>查询 / 筛选 / 统计 / 安全警报</td></tr>
    <tr><td>敏感词</td><td>test_sensitive_word.py</td><td>CRUD / 批量 / 级别 / 重复检测</td></tr>
    <tr><td>WebSocket</td><td>test_websocket.py</td><td>连接 / 认证 / 消息 / 心跳 / 并发</td></tr>
    <tr><td>健康检查</td><td>test_health.py</td><td>健康探针 / 就绪探针</td></tr>
    <tr><td colspan="3" style="background:#f0f0f0;font-weight:600">集成测试</td></tr>
    <tr><td>用户旅程</td><td>test_01_user_journey.py</td><td>注册→登录→对话→评价→统计</td></tr>
    <tr><td>知识库RAG</td><td>test_02_knowledge_rag_flow.py</td><td>创建→导入→索引→检索→RAG对话</td></tr>
    <tr><td>监控流程</td><td>test_03_monitoring_flow.py</td><td>多轮对话→统计→质量评估</td></tr>
    <tr><td>支付订阅</td><td>test_04_payment_subscription_flow.py</td><td>订阅→变更→取消续费</td></tr>
    <tr><td>管理运营</td><td>test_05_admin_operations_flow.py</td><td>管理员登录→租户管理→敏感词→审计</td></tr>
    <tr><td colspan="3" style="background:#f0f0f0;font-weight:600">前端 E2E 测试</td></tr>
    <tr><td>认证流程</td><td>auth.spec.ts</td><td>注册 / 登录 / 登出 / 路由保护</td></tr>
    <tr><td>Dashboard</td><td>dashboard.spec.ts</td><td>页面加载 / 统计卡片 / 导航</td></tr>
    <tr><td>对话功能</td><td>chat.spec.ts</td><td>对话列表 / 发送消息 / 聊天窗口</td></tr>
    <tr><td>知识库</td><td>knowledge.spec.ts</td><td>列表 / 搜索 / 上传 / 检索测试</td></tr>
    <tr><td>设置页面</td><td>settings.spec.ts</td><td>模型配置 / API Key / 通知</td></tr>
  </table>
</div>

<div class="section report-links">
  <h2>详细报告文件</h2>
  <p>
    <a href="backend_report_${TIMESTAMP}.html">后端测试报告 (HTML)</a>
    <a href="frontend_report_${TIMESTAMP}/index.html">前端E2E报告 (Playwright)</a>
    <a href="backend_output_${TIMESTAMP}.log">后端测试日志</a>
    <a href="frontend_output_${TIMESTAMP}.log">前端测试日志</a>
  </p>
</div>

<div class="footer">
  <p>电商智能客服系统 - 自动化测试报告 | $(date '+%Y')</p>
</div>
</div>
</body>
</html>
EOF

echo -e "${GREEN}  ✓ 汇总报告已生成: $SUMMARY_FILE${NC}"

# ==================== 结果 ====================
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  测试执行完成${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_EXIT -eq 0 ]; then
        echo -e "  后端: ${GREEN}✓ 通过${NC}"
    else
        echo -e "  后端: ${RED}✗ 失败${NC}"
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_EXIT -eq 0 ]; then
        echo -e "  前端: ${GREEN}✓ 通过${NC}"
    else
        echo -e "  前端: ${RED}✗ 失败${NC}"
    fi
fi

echo ""
echo -e "  报告目录: ${BLUE}$REPORT_DIR${NC}"
echo -e "  汇总报告: ${BLUE}$SUMMARY_FILE${NC}"
echo ""

# 退出码: 任一失败则非零
TOTAL_EXIT=$((BACKEND_EXIT + FRONTEND_EXIT))
if [ $TOTAL_EXIT -ne 0 ]; then
    echo -e "${YELLOW}  提示: 有测试失败，请查看详细报告${NC}"
    exit 1
fi

echo -e "${GREEN}  所有测试通过！${NC}"
exit 0
