# Jenkins CI/CD 测试配置 - 快速参考

## 🚀 快速开始

### 1. 确认文件已创建

```bash
cd /opt/projects/ecom-chat-bot

# 检查关键文件
ls -la Jenkinsfile                      # Jenkins流水线配置
ls -la CI_CD_TESTING_GUIDE.md          # CI/CD详细指南
ls -la backend/tests/run_ci_tests.sh   # CI测试脚本
```

### 2. 在Jenkins中配置项目

#### 方式A: 使用流水线项目

1. **创建流水线项目**
   - Jenkins首页 → 新建任务
   - 输入名称: `ecom-chatbot-cicd`
   - 选择: Pipeline (流水线)
   - 点击确定

2. **配置Pipeline**
   - 定义: Pipeline script from SCM
   - SCM: Git
   - Repository URL: `https://gitee.com/你的用户名/ecom-chat-bot.git`
   - 分支: `*/main` (或你的主分支)
   - Script Path: `Jenkinsfile`
   - 保存

3. **配置Gitee Webhook (自动触发)**
   - Gitee项目 → 管理 → WebHooks
   - URL: `http://你的Jenkins地址/gitee-project/ecom-chatbot-cicd`
   - 勾选: Push, Pull Request
   - 添加WebHook

#### 方式B: 使用Multibranch Pipeline

1. **创建多分支流水线**
   - Jenkins首页 → 新建任务
   - 选择: Multibranch Pipeline
   
2. **配置分支源**
   - 添加源 → Gitee
   - 配置仓库URL和凭据
   - 保存

### 3. 首次运行测试

点击"立即构建"，观察流水线执行：

```
✓ 准备
✓ 同步代码
✓ Docker配置检查
✓ 检查是否需要重建镜像
✓ 构建镜像 (如需要)
✓ 部署新服务
✓ 健康检查
✓ 部署验证
✓ 运行自动化测试 ⭐️ 新增
```

---

## 📊 查看测试报告

### 在Jenkins界面

1. **测试趋势**
   - 项目首页 → 左侧菜单
   - 可以看到历史测试趋势图

2. **最新构建的测试报告**
   - 点击最新构建 (#编号)
   - 左侧菜单:
     - `测试报告` - HTML测试详情
     - `覆盖率报告` - 代码覆盖率
     - `Test Result` - JUnit测试结果
     - `Build Artifacts` - 下载所有报告

3. **测试历史对比**
   - 项目首页 → Test Result Trend
   - 查看测试通过率变化

### 在服务器上

```bash
cd /opt/projects/ecom-chat-bot/backend/test-reports

# 查看测试摘要
cat test-summary.txt

# 在浏览器中查看HTML报告 (需要本地访问)
# test-report.html
# coverage-html/index.html
```

---

## 🔧 必需的Jenkins插件

确保已安装以下插件:

```
✓ Pipeline                    # 流水线支持
✓ Git plugin                  # Git集成
✓ Gitee Plugin               # Gitee集成
✓ JUnit Plugin               # JUnit报告
✓ HTML Publisher Plugin      # HTML报告发布
✓ Cobertura Plugin (可选)    # 覆盖率报告
✓ DingTalk (可选)            # 钉钉通知
```

安装方法:
- Jenkins → 系统管理 → 插件管理
- 搜索插件名称并安装
- 重启Jenkins

---

## 📝 关键配置说明

### Jenkinsfile 核心部分

```groovy
// 新增的测试阶段
stage('运行自动化测试') {
    steps {
        script {
            sh '''
                cd ${DEPLOY_PATH}/backend
                ./tests/run_ci_tests.sh || true
            '''
        }
    }
}

// 测试报告发布
post {
    always {
        // JUnit测试结果
        junit 'test-reports/junit-report.xml'
        
        // HTML测试报告
        publishHTML([
            reportName: '测试报告',
            reportFiles: 'test-report.html'
        ])
        
        // 覆盖率报告
        publishHTML([
            reportName: '覆盖率报告',
            reportFiles: 'index.html'
        ])
    }
}
```

### 测试脚本功能

`run_ci_tests.sh` 自动执行:
1. ✅ 检查Python环境
2. ✅ 安装测试依赖
3. ✅ 等待服务就绪
4. ✅ 运行测试套件
5. ✅ 生成多种格式报告
6. ✅ 创建测试摘要

---

## 🎯 测试策略配置

### 当前策略 (推荐)

```bash
# 运行快速测试，跳过慢速测试
pytest -m "not slow"
```

优点:
- ⚡️ 快速反馈 (通常<5分钟)
- 🎯 覆盖核心功能
- 💰 节省CI资源

### 可选策略

#### 策略1: 运行所有测试

```bash
# 在 run_ci_tests.sh 中修改
pytest tests/ -v  # 移除 -m "not slow"
```

#### 策略2: 分阶段测试

```bash
# 快速测试
pytest -m "smoke or fast"

# 完整测试
pytest tests/
```

#### 策略3: 按模块测试

```bash
# 只测试修改的模块
pytest tests/test_03_tenant.py \
       tests/test_04_conversation.py
```

---

## 🐛 常见问题快速解决

### 问题1: 测试报告未显示

**症状**: Jenkins构建成功，但没有测试报告链接

**解决**:
```bash
# 1. 检查报告是否生成
cd /opt/projects/ecom-chat-bot/backend
ls -la test-reports/

# 2. 检查插件
# Jenkins → 系统管理 → 插件管理
# 确认已安装: JUnit Plugin, HTML Publisher Plugin

# 3. 检查Jenkinsfile语法
# 确保 publishHTML 配置正确
```

### 问题2: 测试失败

**症状**: 测试用例执行失败

**解决**:
```bash
# 1. 查看测试日志
cat /opt/projects/ecom-chat-bot/backend/test-reports/logs/test-output.log

# 2. 手动运行测试
cd /opt/projects/ecom-chat-bot/backend
./tests/run_ci_tests.sh

# 3. 检查服务状态
docker-compose ps

# 4. 查看API日志
docker-compose logs api --tail=50
```

### 问题3: 依赖安装失败

**症状**: pip安装测试依赖报错

**解决**:
```bash
# 1. 手动安装依赖
pip3 install -r backend/tests/requirements-test.txt

# 2. 检查Python版本
python3 --version  # 需要 ≥3.9

# 3. 升级pip
pip3 install --upgrade pip

# 4. 使用国内镜像
pip3 install -r backend/tests/requirements-test.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题4: 权限问题

**症状**: Permission denied

**解决**:
```bash
# 赋予脚本执行权限
chmod +x /opt/projects/ecom-chat-bot/backend/tests/run_ci_tests.sh

# 检查目录权限
ls -la /opt/projects/ecom-chat-bot/backend/
```

---

## 📈 监控测试质量

### 关键指标

在Jenkins项目首页查看:

1. **测试通过率趋势**
   - 目标: ≥95%
   - 监控: 是否下降

2. **代码覆盖率**
   - 目标: ≥90%
   - 当前: 91%

3. **测试执行时间**
   - 目标: <5分钟
   - 优化: 移除慢速测试

4. **失败用例分析**
   - 频繁失败: 可能是不稳定测试
   - 新增失败: 代码质量问题

### 质量门禁 (可选)

在Jenkinsfile中添加质量检查:

```groovy
stage('质量门禁') {
    steps {
        script {
            // 检查测试通过率
            def testResults = junit 'test-reports/junit-report.xml'
            def passRate = testResults.passCount / testResults.totalCount * 100
            
            if (passRate < 95) {
                error "测试通过率过低: ${passRate}%"
            }
            
            // 检查覆盖率
            def coverage = sh(
                script: "grep -oP 'line-rate=\"\\K[0-9.]+' test-reports/coverage.xml | head -1",
                returnStdout: true
            ).trim().toFloat() * 100
            
            if (coverage < 90) {
                error "代码覆盖率过低: ${coverage}%"
            }
        }
    }
}
```

---

## 🔔 通知配置

### 钉钉通知

1. **获取Webhook**
   - 钉钉群 → 群设置 → 智能群助手 → 添加机器人
   - 选择"自定义"机器人
   - 复制Webhook地址

2. **在Jenkinsfile中配置**
   ```groovy
   environment {
       DINGTALK_WEBHOOK = 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN'
   }
   ```

3. **测试通知**
   - 触发一次构建
   - 检查钉钉群是否收到消息

### 邮件通知

```groovy
post {
    failure {
        emailext (
            subject: "构建失败: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                <p>部署失败，请及时处理！</p>
                <p><a href="${env.BUILD_URL}">查看详情</a></p>
            """,
            to: 'team@example.com'
        )
    }
}
```

---

## 📋 验证清单

部署完成后，请逐项检查:

### Jenkins配置
- [ ] 流水线项目已创建
- [ ] Gitee仓库已连接
- [ ] Jenkinsfile路径正确
- [ ] 必需插件已安装
- [ ] 首次构建成功

### 测试集成
- [ ] 测试阶段正常执行
- [ ] 测试报告成功生成
- [ ] JUnit报告可查看
- [ ] HTML报告可访问
- [ ] 覆盖率报告可访问
- [ ] 构建产物可下载

### 自动化
- [ ] Gitee Webhook已配置
- [ ] 推送代码自动触发构建
- [ ] 测试自动运行
- [ ] 报告自动发布

### 通知 (可选)
- [ ] 钉钉通知正常
- [ ] 邮件通知正常

---

## 📚 下一步

1. **查看详细文档**
   ```bash
   cat /opt/projects/ecom-chat-bot/CI_CD_TESTING_GUIDE.md
   ```

2. **优化测试用例**
   - 补充缺失的测试
   - 优化慢速测试
   - 提高覆盖率

3. **定期审查**
   - 每周查看测试趋势
   - 分析失败用例
   - 持续改进

---

## 🎉 完成

✅ 恭喜！您已成功将测试集成到Jenkins CI/CD流水线！

**效果**:
- 🚀 每次部署自动运行测试
- 📊 自动生成测试报告
- 🔔 异常及时通知
- 📈 持续监控代码质量

---

**创建日期**: 2026-02-09  
**更新日期**: 2026-02-09  
**维护**: DevOps Team
