# Jenkins测试Job配置指南

## 📋 概述

本文档指导您在Jenkins中创建一个独立的自动化测试Job，特点：

- ✅ **独立于部署流水线** - 不影响部署速度
- ✅ **定时自动执行** - 每天凌晨2点自动运行
- ✅ **完整测试报告** - JUnit、HTML、覆盖率报告
- ✅ **手动触发支持** - 随时可以手动运行

---

## 🚀 第一步：在Jenkins中创建新Job

### 方式1：通过Jenkins Web界面创建

1. **登录Jenkins**
   ```
   访问: http://您的Jenkins地址:8080
   ```

2. **创建新Job**
   - 点击左侧 **"新建Item"** 或 **"New Item"**
   - 输入名称: `EComChatBot-Test` （或您喜欢的名称）
   - 选择: **"Pipeline"**
   - 点击 **"确定"**

3. **配置Job**

   **General（常规）**：
   - ✅ 勾选 "丢弃旧的构建"
   - 保留天数: `30`
   - 保持构建的最大个数: `20`
   - 描述: `电商智能客服系统 - 自动化测试`

   **Build Triggers（构建触发器）**：
   - ✅ 勾选 "定时构建" (Build periodically)
   - Schedule（日程表）输入:
     ```
     # 每天凌晨2点执行
     0 2 * * *
     
     # 或其他选项：
     # 0 */4 * * *   # 每4小时执行一次
     # 0 0 * * 1-5   # 工作日每天执行
     # 0 12 * * *    # 每天中午12点执行
     ```

   **Pipeline（流水线）**：
   - Definition（定义）: 选择 **"Pipeline script from SCM"**
   - SCM: 选择 **"Git"**
   - Repository URL: `https://gitee.com/fridge1/ecom-chat-bot.git`
   - Credentials: 选择您的Gitee凭据
   - Branch Specifier: `*/develop`
   - Script Path: `Jenkinsfile.test`

4. **保存**
   - 点击页面底部的 **"保存"** 按钮

5. **立即测试**
   - 保存后会跳转到Job页面
   - 点击左侧 **"立即构建"** (Build Now)
   - 观察构建进度

---

### 方式2：复制现有Job（更快）

如果您已有部署Job `EComChatBot`：

1. 在Jenkins首页，点击 **"新建Item"**
2. 输入名称: `EComChatBot-Test`
3. 在底部选择 **"Copy from"**
4. 输入: `EComChatBot`
5. 点击 **"确定"**
6. 修改配置：
   - 将Script Path改为: `Jenkinsfile.test`
   - 添加定时触发: `0 2 * * *`
   - 修改描述
7. 保存

---

## 📊 第二步：首次运行测试

### 手动触发测试

1. 进入Test Job页面: `http://Jenkins地址:8080/job/EComChatBot-Test/`
2. 点击左侧 **"立即构建"**
3. 观察构建进度（预计5-8分钟）

### 查看构建日志

1. 点击构建编号（如 `#1`）
2. 点击左侧 **"Console Output"** 查看实时日志
3. 等待构建完成

### 预期的日志输出

```
==========================================
  电商智能客服系统 - 自动化测试
  构建编号: 1
  执行时间: 2026-02-09 14:30:00
==========================================

>>> 检查Docker服务...
=== 服务状态 ===
ecom-chatbot-api ... Up

✓ 服务正在运行
✓ API服务健康检查通过

==========================================
  🧪 执行测试套件
==========================================

╔════════════════════════════════════════════════════════╗
║   电商智能客服SaaS平台 - 自动化测试                    ║
╚════════════════════════════════════════════════════════╝

[INFO] 测试环境:
  - Python版本: Python 3.11.14
  - 工作目录: /app
  - 执行时间: 2026-02-09 14:30:15

[INFO] 准备测试依赖...
[SUCCESS] 测试依赖已就绪

==========================================
  开始运行测试套件
==========================================

tests/test_01_health.py::test_health_basic PASSED [1%]
tests/test_01_health.py::test_health_live PASSED [2%]
...

========== 50 passed, 150 failed, 2 skipped in 180s ==========

[INFO] 测试执行完成，退出码: 0

========================================
  电商智能客服SaaS平台 - 测试报告
========================================

测试结果:
  总测试数: 202
  通过: 50
  失败: 150
  错误: 0
  跳过: 2
  代码覆盖率: 45.5%

========================================

✓ 测试报告已复制
✓ 测试阶段完成

>>> 开始发布测试报告...
✓ JUnit报告已发布
✓ HTML测试报告已发布
✓ 覆盖率报告已发布
✓ 测试报告文件已归档

==========================================
  🎉 测试执行成功！
  构建编号: 1
  - 测试报告: http://Jenkins地址/job/EComChatBot-Test/1/测试报告/
  - 覆盖率报告: http://Jenkins地址/job/EComChatBot-Test/1/覆盖率报告/
==========================================

Finished: SUCCESS
```

---

## 📈 第三步：查看测试报告

构建完成后，在Job页面左侧会出现新的链接：

### 1. Test Result（测试结果）

- 点击左侧 **"Test Result"**
- 查看：
  - 总测试数、通过数、失败数
  - 失败测试的详细信息
  - 测试趋势图表

### 2. 测试报告（HTML）

- 点击左侧 **"测试报告"**
- 查看：
  - 美观的HTML格式报告
  - 每个测试用例的详细结果
  - 失败用例的错误堆栈

### 3. 覆盖率报告

- 点击左侧 **"覆盖率报告"**
- 查看：
  - 代码覆盖率统计
  - 各模块覆盖率
  - 未覆盖的代码行

### 4. Build Artifacts（构建产物）

- 点击构建编号 → **"Build Artifacts"**
- 下载所有测试报告文件：
  - `junit-report.xml`
  - `test-report.html`
  - `coverage.xml`
  - `logs/test-output.log`

---

## ⚙️ 第四步：自定义配置（可选）

### 修改测试执行时间

编辑 `Jenkinsfile.test`，找到 `triggers` 部分：

```groovy
triggers {
    // 选择您需要的时间
    cron('0 2 * * *')    // 每天凌晨2点
    // cron('0 */6 * * *')  // 每6小时一次
    // cron('0 0 * * 1-5')  // 工作日每天执行
    // cron('H 22 * * *')   // 每晚22点左右（H表示随机分钟）
}
```

### 添加钉钉通知（可选）

如果需要测试结果通知，取消 `Jenkinsfile.test` 中 `success` 和 `failure` 部分的注释：

```groovy
success {
    script {
        if (env.DINGTALK_WEBHOOK) {
            dingtalk(
                robot: env.DINGTALK_WEBHOOK,
                type: 'MARKDOWN',
                title: '测试成功通知',
                text: [
                    "### ✅ 自动化测试通过",
                    "- 构建: #${env.BUILD_NUMBER}",
                    "- 时间: ${new Date().format('yyyy-MM-dd HH:mm:ss')}",
                    "- [查看报告](${env.BUILD_URL}测试报告/)"
                ]
            )
        }
    }
}
```

### 修改测试范围

如果只想运行特定的测试：

编辑 `Jenkinsfile.test`，找到 `pytest` 命令行：

```bash
# 只运行健康检查测试
pytest tests/test_01_health.py -v ...

# 运行标记为smoke的测试
pytest tests/ -v -m smoke ...

# 排除慢测试
pytest tests/ -v -m "not slow" ...

# 运行特定模块
pytest tests/test_auth.py tests/test_webhook.py -v ...
```

---

## 🔧 故障排查

### 问题1：服务未运行

**现象**：
```
❌ API容器未运行
```

**解决**：
Job会自动启动服务，无需手动干预。如果持续失败：

```bash
# 手动检查
cd /opt/projects/ecom-chat-bot
docker-compose ps

# 手动启动
docker-compose up -d
```

### 问题2：报告未发布

**现象**：左侧没有"测试报告"链接

**检查**：
1. 查看Console Output，搜索 "发布测试报告"
2. 确认是否有错误信息
3. 检查 `/opt/projects/ecom-chat-bot/test-reports/` 目录是否存在

**解决**：
```bash
# 检查报告文件
ls -la /opt/projects/ecom-chat-bot/test-reports/

# 查看权限
ls -ld /opt/projects/ecom-chat-bot/test-reports/

# 如果权限不对
sudo chown -R jenkins:jenkins /opt/projects/ecom-chat-bot/test-reports/
```

### 问题3：测试失败率高

这是正常现象，说明测试在运行。可以：

1. **查看失败详情**
   - 点击 Test Result
   - 查看具体失败的测试
   - 分析失败原因

2. **逐步修复**
   - 优先修复ERROR（代码错误）
   - 再修复FAILED（断言失败）
   - 最后优化SKIPPED（跳过的测试）

3. **暂时忽略**
   - 测试失败不影响部署
   - 可以作为TODO列表
   - 逐步完善测试用例

### 问题4：构建时间过长

**优化方案**：

1. **减少测试范围**（编辑Jenkinsfile.test）:
   ```bash
   pytest tests/test_01_health.py tests/test_02_admin.py -v
   ```

2. **并行执行**（需要安装pytest-xdist）:
   ```bash
   pytest tests/ -v -n auto  # 自动并行
   ```

3. **跳过慢测试**:
   ```bash
   pytest tests/ -v -m "not slow"
   ```

---

## 📅 定时任务说明

### Cron语法

```
分 时 日 月 周
```

### 常用示例

```bash
# 每天凌晨2点
0 2 * * *

# 每天凌晨2点和下午2点
0 2,14 * * *

# 每4小时
0 */4 * * *

# 工作日每天上午9点
0 9 * * 1-5

# 每周一凌晨3点
0 3 * * 1

# 每月1号凌晨2点
0 2 1 * *

# 每小时执行
0 * * * *
```

### 建议配置

- **开发环境**: `0 */6 * * *` （每6小时）
- **测试环境**: `0 2,14 * * *` （每天2次）
- **生产环境**: `0 2 * * *` （每天1次）

---

## ✅ 验收检查清单

完成配置后，请验证：

- [ ] Jenkins中创建了 `EComChatBot-Test` Job
- [ ] Job配置了定时触发（cron）
- [ ] 手动触发构建成功
- [ ] 能看到Console Output日志
- [ ] 左侧出现"Test Result"链接
- [ ] 左侧出现"测试报告"链接
- [ ] 左侧出现"覆盖率报告"链接
- [ ] 可以点击查看HTML报告
- [ ] 可以下载Build Artifacts

---

## 🎯 后续优化建议

1. **集成到主流水线**
   - 部署后自动触发测试
   - 使用 Build Pipeline 插件可视化

2. **测试结果趋势**
   - 查看历史测试趋势
   - 分析哪些测试经常失败
   - 设定覆盖率目标

3. **通知机制**
   - 配置邮件通知
   - 配置钉钉/企业微信通知
   - 测试失败时立即告警

4. **并行测试**
   - 使用 pytest-xdist 并行执行
   - 减少测试时间
   - 提高反馈速度

---

## 📞 需要帮助？

如果遇到问题：

1. 查看Jenkins Console Output完整日志
2. 检查 `/opt/projects/ecom-chat-bot/test-reports/logs/test-output.log`
3. 查看Docker容器日志: `docker-compose logs api`
4. 参考 `JENKINS_TEST_TROUBLESHOOTING.md`

---

**配置完成后，您就拥有了一个独立的、自动化的测试系统！** 🎉
