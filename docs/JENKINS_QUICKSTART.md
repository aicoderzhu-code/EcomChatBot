# Jenkins CI/CD 快速开始指南

> 5分钟快速配置Jenkins自动部署流水线

## 📝 前提条件

- ✅ Jenkins已安装 (http://115.190.75.88:8080)
- ✅ Jenkins已登录 (zhulang/hhjy2026@Zl)
- ✅ 所需插件已安装
- ✅ 项目代码已提交到Git仓库

---

## 🚀 快速开始（3步完成）

### 第一步: 初始化服务器环境

```bash
# SSH登录到Jenkins服务器
ssh zhulang@115.190.75.88

# 进入项目目录
cd /Users/zhulang/work/ecom-chat-bot

# 运行初始化脚本
sudo bash scripts/init-deployment.sh

# 根据提示修改生产环境配置
sudo vi /opt/ecom-chat-bot/shared/.env.production
# 主要检查: JWT_SECRET, DEEPSEEK_API_KEY, CORS_ORIGINS

# 确保基础服务运行
docker-compose up -d postgres redis milvus rabbitmq
docker-compose ps  # 检查状态
```

**预计时间**: 2分钟

---

### 第二步: 创建Jenkins Pipeline Job

#### 2.1 创建主流水线

```
1. 打开Jenkins: http://115.190.75.88:8080
2. 点击 "新建Item"
3. 输入名称: ecom-chatbot-cicd-pipeline
4. 选择: Pipeline
5. 点击 "OK"

配置Pipeline:
  Definition: Pipeline script from SCM
  SCM: Git
  Repository URL: <你的Git仓库地址>
  Branch: */develop
  Script Path: Jenkinsfile
  
  ☑ Lightweight checkout

6. 点击 "Save"
```

#### 2.2 创建手动测试Job

```
1. 点击 "新建Item"
2. 输入名称: ecom-chatbot-manual-test
3. 选择: Pipeline
4. 点击 "OK"

配置Pipeline:
  Definition: Pipeline script from SCM
  SCM: Git
  Repository URL: <你的Git仓库地址>
  Branch: */develop
  Script Path: Jenkinsfile.manual-test
  
  ☑ Lightweight checkout

5. 点击 "Save"
```

**预计时间**: 2分钟

---

### 第三步: 配置Git Webhook (可选)

如果需要自动触发，配置Webhook:

#### Gitee

```
1. 进入Gitee仓库设置
2. 管理 > WebHooks > 添加

URL: http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token
触发事件: ☑ Push
分支: develop

3. 添加并测试
```

#### GitHub

```
1. 进入GitHub仓库设置
2. Settings > Webhooks > Add webhook

Payload URL: http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token
Content type: application/json
Events: ☑ Just the push event

3. Add webhook
```

**预计时间**: 1分钟

---

## ✅ 验证安装

### 测试自动部署

```bash
# 1. 提交代码测试
git add .
git commit -m "test: trigger jenkins pipeline"
git push origin develop

# 2. 查看Jenkins
打开: http://115.190.75.88:8080/job/ecom-chatbot-cicd-pipeline/

# 3. 应该看到新的构建开始执行
点击构建号 > Console Output 查看日志
```

### 测试手动测试Job

```
1. 打开: http://115.190.75.88:8080/job/ecom-chatbot-manual-test/
2. 点击 "Build with Parameters"
3. 选择参数:
   - BUILD_NUMBER: latest
   - TEST_URL: http://115.190.75.88:8000
   - TEST_SUITE: smoke
4. 点击 "Build"
5. 查看测试报告
```

### 验证服务运行

```bash
# 检查服务健康
curl http://115.190.75.88:8000/health

# 查看API文档
curl http://115.190.75.88:8000/docs

# 查看容器状态
docker ps --filter "name=ecom-chatbot"
```

---

## 📊 工作流程

```
开发者提交代码
    ↓
Git Push to develop
    ↓
Webhook触发Jenkins
    ↓
Jenkins执行流水线
    ├─ 拉取代码
    ├─ 构建镜像
    ├─ 运行测试 (30-60min)
    ├─ 部署服务
    └─ 冒烟测试
    ↓
部署成功
    ↓
触发手动测试Job
    ↓
手动测试入口就绪
```

---

## 🎯 使用方式

### 方式1: 自动部署 (推荐)

```bash
# 直接推送代码即可，Jenkins自动部署
git push origin develop
```

### 方式2: 手动触发

```
Jenkins > ecom-chatbot-cicd-pipeline > Build Now
```

### 方式3: 参数化构建

```
Jenkins > ecom-chatbot-cicd-pipeline > Build with Parameters
  SKIP_TESTS: false        # 是否跳过测试
  FORCE_DEPLOY: false      # 强制部署
  REBUILD_IMAGE: false     # 重建镜像
```

---

## 📱 查看状态

### Jenkins Dashboard

```
主页: http://115.190.75.88:8080
CI/CD: http://115.190.75.88:8080/job/ecom-chatbot-cicd-pipeline/
测试: http://115.190.75.88:8080/job/ecom-chatbot-manual-test/
```

### 应用服务

```
健康检查: http://115.190.75.88:8000/health
API文档: http://115.190.75.88:8000/docs
ReDoc: http://115.190.75.88:8000/redoc
```

### 查看日志

```bash
# API服务日志
docker logs -f ecom-chatbot-api

# Celery日志
docker logs -f ecom-chatbot-celery

# 所有服务日志
docker-compose logs -f
```

---

## 🔧 常用命令

```bash
# 查看容器状态
docker ps --filter "name=ecom-chatbot"

# 重启服务
docker restart ecom-chatbot-api ecom-chatbot-celery

# 查看部署目录
ls -la /opt/ecom-chat-bot/

# 手动执行部署
sudo bash /opt/ecom-chat-bot/jenkins-deploy.sh <BUILD_NUMBER>

# 手动执行冒烟测试
bash scripts/smoke-test.sh http://localhost:8000

# 清理Docker资源
docker system prune -a
```

---

## ⚠️ 重要提示

1. **首次部署**可能需要60-90分钟（包含完整测试）
2. **后续部署**约30-45分钟（增量测试）
3. 部署期间服务**不会中断**（滚动更新）
4. 测试失败**不会阻止部署**（但会标记为UNSTABLE）
5. 所有操作都有**详细日志**可查

---

## 🆘 快速故障排查

### 问题1: Jenkins无法触发

```bash
# 检查Webhook配置
curl -X POST "http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token" \
  -H "Content-Type: application/json" \
  -d '{"ref": "refs/heads/develop", "repository": {"name": "ecom-chat-bot"}}'
```

### 问题2: 构建失败

```bash
# 查看构建日志
Jenkins > Job > 构建号 > Console Output

# 检查Docker
docker --version
docker ps

# 检查磁盘空间
df -h
docker system df
```

### 问题3: 服务无法访问

```bash
# 检查容器
docker ps --filter "name=ecom-chatbot"

# 检查日志
docker logs ecom-chatbot-api --tail 100

# 检查端口
sudo lsof -i :8000

# 重启服务
docker restart ecom-chatbot-api
```

### 问题4: 测试一直超时

```bash
# 临时跳过测试
Jenkins > Build with Parameters > SKIP_TESTS: true

# 或使用快速测试
修改TEST_LEVEL参数为: fast
```

---

## 📚 进阶文档

详细文档请查看: [`docs/JENKINS_CICD_GUIDE.md`](JENKINS_CICD_GUIDE.md)

包含:
- 完整的Jenkins配置说明
- 详细的故障排查指南
- 日常维护操作手册
- 监控告警配置
- 性能优化建议

---

## ✅ 完成清单

- [ ] 服务器初始化完成
- [ ] 主流水线Job创建完成
- [ ] 手动测试Job创建完成
- [ ] Git Webhook配置完成（可选）
- [ ] 首次自动部署测试通过
- [ ] 手动测试入口验证通过
- [ ] 团队成员已培训

---

**🎉 恭喜！Jenkins CI/CD流水线配置完成！**

现在您可以：
1. 推送代码自动部署 ✅
2. 运行完整测试 ✅
3. 手动触发测试 ✅
4. 查看详细报告 ✅
5. 接收部署通知 ✅

---

**需要帮助？**
- 📖 查看完整手册: [`docs/JENKINS_CICD_GUIDE.md`](JENKINS_CICD_GUIDE.md)
- 🐛 遇到问题: 查看故障排查章节
- 💬 技术支持: 提交Issue到项目仓库
