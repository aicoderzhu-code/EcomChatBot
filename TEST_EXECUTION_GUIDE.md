# 电商智能客服系统 - 独立测试运行方案

## 📋 目录

1. [方案概述](#方案概述)
2. [方案对比](#方案对比)
3. [推荐方案](#推荐方案)
4. [其他方案](#其他方案)
5. [测试报告查看](#测试报告查看)
6. [问题排查](#问题排查)

---

## 方案概述

有以下几种方式可以独立运行测试：

### 方案1：在运行中的Docker容器中执行（推荐⭐）
- **优势**：环境完全一致、无需额外配置、速度快
- **适用**：日常开发测试、快速验证
- **耗时**：3-5分钟

### 方案2：创建专门的测试脚本
- **优势**：可重复使用、易于集成到工作流
- **适用**：频繁测试、自动化场景
- **耗时**：首次5分钟，后续3分钟

### 方案3：本地虚拟环境运行
- **优势**：调试方便、可单独运行某个测试
- **适用**：开发调试、测试编写
- **耗时**：首次10分钟，后续2分钟

### 方案4：创建独立的Jenkins测试Job
- **优势**：定时执行、独立于部署、生成报告
- **适用**：持续测试、夜间回归测试
- **耗时**：5-8分钟

---

## 方案对比

| 方案 | 环境一致性 | 配置难度 | 执行速度 | 适用场景 | 推荐度 |
|------|-----------|---------|---------|---------|--------|
| Docker容器 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 快速验证 | ⭐⭐⭐⭐⭐ |
| 测试脚本 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 自动化 | ⭐⭐⭐⭐ |
| 本地环境 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 开发调试 | ⭐⭐⭐ |
| Jenkins Job | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 定时测试 | ⭐⭐⭐⭐ |

---

## 推荐方案：方案1 - Docker容器中执行

### 🎯 为什么推荐？

1. ✅ **环境完全一致** - 与部署环境相同
2. ✅ **无需配置** - 服务已运行，依赖已安装
3. ✅ **快速执行** - 直接运行，3-5分钟完成
4. ✅ **结果准确** - 真实环境测试

### 📝 执行步骤

#### 步骤1：进入项目目录

```bash
cd /opt/projects/ecom-chat-bot
```

#### 步骤2：运行完整测试

```bash
# 进入Docker容器并运行测试
docker-compose exec api bash << 'EOF'
    # 设置Python路径
    export PYTHONPATH=/app:$PYTHONPATH
    
    # 创建报告目录
    mkdir -p /app/test-reports/coverage-html
    
    # 运行所有测试
    pytest tests/ \
        -v \
        --tb=short \
        --junit-xml=/app/test-reports/junit-report.xml \
        --html=/app/test-reports/test-report.html \
        --self-contained-html \
        --cov=api \
        --cov=services \
        --cov=models \
        --cov-report=html:/app/test-reports/coverage-html \
        --cov-report=xml:/app/test-reports/coverage.xml \
        --cov-report=term
    
    echo ""
    echo "✓ 测试完成！"
    echo "报告位置: /app/test-reports/"
EOF

# 复制报告到宿主机
docker cp ecom-chatbot-api:/app/test-reports ./test-reports
echo "✓ 报告已复制到: $(pwd)/test-reports"
```

#### 步骤3：查看测试结果

```bash
# 查看测试摘要
cat test-reports/test-summary.txt

# 在浏览器中查看HTML报告
# test-reports/test-report.html

# 查看覆盖率报告
# test-reports/coverage-html/index.html
```

### ⚡ 快捷命令（推荐）

为了方便使用，可以创建一个快捷脚本：

```bash
# 创建测试脚本
cat > /opt/projects/ecom-chat-bot/run_tests.sh << 'SCRIPT_EOF'
#!/bin/bash
###############################################################################
# 电商智能客服系统 - 快速测试脚本
# 用途: 在Docker容器中运行测试
###############################################################################

set -e

cd /opt/projects/ecom-chat-bot

echo "╔════════════════════════════════════════════════════════╗"
echo "║   电商智能客服系统 - 测试执行                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 检查容器是否运行
if ! docker-compose ps | grep -q "ecom-chatbot-api.*Up"; then
    echo "❌ API容器未运行，请先启动服务："
    echo "   cd /opt/projects/ecom-chat-bot && docker-compose up -d"
    exit 1
fi

echo "[INFO] 在Docker容器中运行测试..."
echo ""

# 运行测试
docker-compose exec -T api bash << 'EOF'
export PYTHONPATH=/app:$PYTHONPATH

# 创建报告目录
mkdir -p /app/test-reports/coverage-html
mkdir -p /app/test-reports/logs

echo "开始执行测试套件..."
echo ""

# 执行测试
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
    2>&1 | tee /app/test-reports/logs/test-output.log

echo ""
echo "✓ 测试执行完成！"
EOF

# 复制报告到宿主机
echo ""
echo "[INFO] 复制测试报告到宿主机..."
docker cp ecom-chatbot-api:/app/test-reports ./test-reports 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   测试完成                                             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📊 测试报告位置:"
echo "  - HTML报告: $(pwd)/test-reports/test-report.html"
echo "  - 覆盖率报告: $(pwd)/test-reports/coverage-html/index.html"
echo "  - JUnit XML: $(pwd)/test-reports/junit-report.xml"
echo "  - 测试日志: $(pwd)/test-reports/logs/test-output.log"
echo ""
echo "💡 查看报告:"
echo "  浏览器打开: file://$(pwd)/test-reports/test-report.html"
echo ""

SCRIPT_EOF

# 添加执行权限
chmod +x /opt/projects/ecom-chat-bot/run_tests.sh

echo "✓ 测试脚本已创建: /opt/projects/ecom-chat-bot/run_tests.sh"
```

使用快捷脚本：

```bash
# 直接运行
/opt/projects/ecom-chat-bot/run_tests.sh

# 或
cd /opt/projects/ecom-chat-bot && ./run_tests.sh
```

---

## 其他方案

### 方案2：专门的测试脚本（带安装依赖）

适合首次运行或依赖变更后使用：

```bash
# 创建完整测试脚本
cat > /opt/projects/ecom-chat-bot/run_tests_full.sh << 'FULL_SCRIPT'
#!/bin/bash
###############################################################################
# 电商智能客服系统 - 完整测试脚本（含依赖安装）
###############################################################################

set -e

cd /opt/projects/ecom-chat-bot

echo "╔════════════════════════════════════════════════════════╗"
echo "║   电商智能客服系统 - 完整测试执行                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 在容器中执行测试
docker-compose exec -T api bash << 'EOF'
set -e

echo "[INFO] 安装测试依赖..."
pip install -q pytest pytest-asyncio pytest-cov pytest-html httpx faker aiosqlite

echo "[INFO] 设置环境..."
export PYTHONPATH=/app:$PYTHONPATH

echo "[INFO] 创建报告目录..."
mkdir -p /app/test-reports/coverage-html /app/test-reports/logs

echo ""
echo "=========================================="
echo "  开始运行测试"
echo "=========================================="
echo ""

# 运行测试
pytest tests/ \
    -v \
    --tb=short \
    --junit-xml=/app/test-reports/junit-report.xml \
    --html=/app/test-reports/test-report.html \
    --self-contained-html \
    --cov=api \
    --cov=services \
    --cov=models \
    --cov-report=html:/app/test-reports/coverage-html \
    --cov-report=xml:/app/test-reports/coverage.xml \
    --cov-report=term

echo ""
echo "✓ 测试完成！"
EOF

# 复制报告
docker cp ecom-chatbot-api:/app/test-reports ./test-reports

echo ""
echo "✓ 报告已保存到: $(pwd)/test-reports"

FULL_SCRIPT

chmod +x /opt/projects/ecom-chat-bot/run_tests_full.sh
```

### 方案3：本地虚拟环境运行

适合开发和调试：

```bash
# 创建虚拟环境
cd /opt/projects/ecom-chat-bot/backend
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-html httpx faker aiosqlite

# 配置环境变量
export PYTHONPATH=/opt/projects/ecom-chat-bot/backend:$PYTHONPATH
export DATABASE_URL="sqlite+aiosqlite:///test.db"

# 运行测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_auth.py -v

# 运行单个测试
pytest tests/test_auth.py::TestTenantLogin::test_login_success -v
```

### 方案4：创建Jenkins测试Job

在Jenkins中创建新的Job：

**Job配置**：

```groovy
pipeline {
    agent any
    
    environment {
        DEPLOY_PATH = '/opt/projects/ecom-chat-bot'
    }
    
    triggers {
        // 每天凌晨2点执行
        cron('0 2 * * *')
    }
    
    stages {
        stage('运行测试') {
            steps {
                sh '''
                    cd ${DEPLOY_PATH}
                    
                    # 检查服务是否运行
                    if ! docker-compose ps | grep -q "ecom-chatbot-api.*Up"; then
                        echo "启动服务..."
                        docker-compose up -d
                        sleep 30
                    fi
                    
                    # 运行测试
                    docker-compose exec -T api bash << 'EOF'
                        export PYTHONPATH=/app:$PYTHONPATH
                        mkdir -p /app/test-reports/coverage-html
                        
                        pytest tests/ \
                            -v \
                            --junit-xml=/app/test-reports/junit-report.xml \
                            --html=/app/test-reports/test-report.html \
                            --self-contained-html \
                            --cov=api --cov=services --cov=models \
                            --cov-report=html:/app/test-reports/coverage-html \
                            --cov-report=xml:/app/test-reports/coverage.xml
EOF
                    
                    # 复制报告
                    docker cp ecom-chatbot-api:/app/test-reports ./backend/test-reports
                '''
            }
        }
    }
    
    post {
        always {
            junit 'backend/test-reports/junit-report.xml'
            publishHTML([
                reportDir: 'backend/test-reports',
                reportFiles: 'test-report.html',
                reportName: '测试报告'
            ])
        }
    }
}
```

---

## 测试报告查看

### HTML报告

```bash
# 在本地查看
firefox test-reports/test-report.html
# 或
google-chrome test-reports/test-report.html
```

### 覆盖率报告

```bash
# 查看覆盖率HTML
firefox test-reports/coverage-html/index.html
```

### 终端查看

```bash
# 查看测试日志
cat test-reports/logs/test-output.log

# 查看测试摘要
cat test-reports/test-summary.txt
```

---

## 问题排查

### 问题1：容器未运行

```bash
# 检查容器状态
docker-compose ps

# 启动服务
docker-compose up -d

# 等待服务就绪
sleep 30
```

### 问题2：模块导入失败

```bash
# 进入容器检查
docker-compose exec api bash

# 检查PYTHONPATH
echo $PYTHONPATH

# 手动设置
export PYTHONPATH=/app:$PYTHONPATH

# 测试导入
python -c "import api; print('OK')"
```

### 问题3：测试依赖缺失

```bash
# 进入容器安装
docker-compose exec api bash
pip install pytest pytest-asyncio pytest-cov pytest-html httpx faker aiosqlite
```

### 问题4：数据库错误

```bash
# 测试使用内存SQLite，不应该有持久化问题
# 如果遇到问题，检查conftest.py配置

# 查看测试数据库配置
docker-compose exec api cat /app/tests/conftest.py | grep -A 5 "create_async_engine"
```

---

## 总结

### 推荐使用顺序

1. **日常快速验证** → 方案1（Docker容器，3分钟）
2. **首次测试** → 方案2（完整脚本，5分钟）
3. **开发调试** → 方案3（本地环境，灵活）
4. **持续集成** → 方案4（Jenkins Job，自动化）

### 下一步

选择方案后，我可以帮您：
1. 创建对应的脚本
2. 执行第一次测试
3. 分析测试结果
4. 修复失败的测试用例

---

**请告诉我您想使用哪个方案，我会帮您立即实施！** 🚀
