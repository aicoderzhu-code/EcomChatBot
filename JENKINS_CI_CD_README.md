# Jenkins CI/CD 自动部署流水线 - 新功能说明

> 本项目已配置完整的Jenkins CI/CD自动部署流水线 🎉

## ✨ 新增功能

### 🚀 自动化部署

- ✅ **代码推送自动部署**: 推送到develop分支自动触发部署
- ✅ **完整测试覆盖**: 30-60分钟全面测试
- ✅ **零停机部署**: Docker滚动更新，无服务中断
- ✅ **自动冒烟测试**: 部署后自动验证服务健康
- ✅ **手动测试入口**: 提供3种方式触发手动测试
- ✅ **通知机制**: 支持企业微信/钉钉通知（可选）

### 📊 流程图

```
开发者提交 → Git Push → Webhook触发 → Jenkins拉取代码 → 构建镜像
    → 运行测试(30-60min) → 测试通过 → 自动部署 → 冒烟测试
    → 部署成功 → 触发手动测试Job → 手动测试就绪
```

## 📁 新增文件

```
项目新增文件:
├── Jenkinsfile                      # 主CI/CD流水线配置
├── Jenkinsfile.manual-test          # 手动测试Job配置
├── docker-compose.prod.yml          # 生产环境Docker配置
├── .env.production.template         # 生产环境配置模板
├── scripts/
│   ├── jenkins-deploy.sh            # 自动部署脚本
│   ├── smoke-test.sh                # 冒烟测试脚本
│   └── init-deployment.sh           # 环境初始化脚本
└── docs/
    ├── JENKINS_QUICKSTART.md        # 快速开始指南
    ├── JENKINS_CICD_GUIDE.md        # 完整使用手册
    └── JENKINS_FILES_README.md      # 文件说明文档
```

## 🎯 快速开始

### 方式1: 使用快速开始指南（推荐新手）

```bash
# 查看快速开始文档
cat docs/JENKINS_QUICKSTART.md

# 或在浏览器中打开
open docs/JENKINS_QUICKSTART.md
```

**5分钟完成配置**，包含:
- 服务器环境初始化
- Jenkins Job创建
- Git Webhook配置
- 首次部署测试

### 方式2: 使用完整手册（推荐深入使用）

```bash
# 查看完整手册
cat docs/JENKINS_CICD_GUIDE.md

# 或在浏览器中打开
open docs/JENKINS_CICD_GUIDE.md
```

包含**详细的配置说明、使用流程、故障排查和维护指南**。

## 🔧 核心组件

### 1. 主CI/CD流水线 (`Jenkinsfile`)

**触发方式**: develop分支代码推送自动触发

**流程**:
1. 代码检出 (1分钟)
2. 环境检查 (30秒)
3. 构建Docker镜像 (3-5分钟)
4. 运行完整测试 (30-60分钟)
5. 部署到生产环境 (2-3分钟)
6. 执行冒烟测试 (1分钟)
7. 触发手动测试Job

**总耗时**: 约40-70分钟

### 2. 手动测试Job (`Jenkinsfile.manual-test`)

**触发方式**: 手动点击或主流水线自动触发

**测试套件**:
- `quick`: 快速测试 (10-15分钟)
- `full`: 完整测试 (30-60分钟，含覆盖率)
- `api`: 仅API测试
- `integration`: 仅集成测试
- `smoke`: 仅冒烟测试

### 3. 部署脚本 (`scripts/jenkins-deploy.sh`)

**功能**:
- 滚动更新部署
- 自动备份当前版本
- 健康检查验证
- 流量无缝切换
- 自动清理旧版本

### 4. 冒烟测试 (`scripts/smoke-test.sh`)

**测试项**:
- ✅ 健康检查端点
- ✅ API文档可访问性
- ✅ 核心业务接口
- ✅ 响应时间性能
- ✅ 容器运行状态

## 📱 访问地址

```bash
# Jenkins平台
http://115.190.75.88:8080
  用户名: zhulang
  密码: hhjy2026@Zl

# CI/CD流水线
http://115.190.75.88:8080/job/ecom-chatbot-cicd-pipeline/

# 手动测试Job
http://115.190.75.88:8080/job/ecom-chatbot-manual-test/

# API服务
http://115.190.75.88:8000
http://115.190.75.88:8000/docs    # API文档
http://115.190.75.88:8000/health  # 健康检查
```

## 🎮 使用方式

### 自动部署（推荐）

```bash
# 开发完成后，直接推送代码
git add .
git commit -m "feat: add new feature"
git push origin develop

# Jenkins自动触发部署，无需其他操作
# 可在Jenkins查看部署进度
```

### 手动触发部署

```
1. 打开Jenkins: http://115.190.75.88:8080
2. 找到 "ecom-chatbot-cicd-pipeline" Job
3. 点击 "Build Now"
4. 查看构建日志和进度
```

### 执行手动测试

```
1. 打开Jenkins: http://115.190.75.88:8080
2. 找到 "ecom-chatbot-manual-test" Job
3. 点击 "Build with Parameters"
4. 选择测试套件（推荐: quick）
5. 点击 "Build"
6. 查看测试报告
```

## 📊 监控和日志

### 查看构建状态

```bash
# Web界面
http://115.190.75.88:8080/job/ecom-chatbot-cicd-pipeline/

# 查看最新构建日志
点击构建号 > Console Output
```

### 查看服务日志

```bash
# API服务日志
docker logs -f ecom-chatbot-api

# Celery日志
docker logs -f ecom-chatbot-celery

# 所有服务日志
docker-compose logs -f
```

### 查看服务状态

```bash
# 容器状态
docker ps --filter "name=ecom-chatbot"

# 健康检查
curl http://115.190.75.88:8000/health

# 详细状态
bash scripts/status.sh
```

## 🔧 常用命令

```bash
# 初始化部署环境（首次运行）
sudo bash scripts/init-deployment.sh

# 手动执行部署
sudo bash scripts/jenkins-deploy.sh <BUILD_NUMBER>

# 手动执行冒烟测试
bash scripts/smoke-test.sh http://localhost:8000

# 重启服务
docker restart ecom-chatbot-api ecom-chatbot-celery

# 查看部署目录
ls -la /opt/ecom-chat-bot/

# 清理Docker资源
docker system prune -a
```

## 🆘 故障排查

### 常见问题

1. **Jenkins无法触发**
   - 检查Webhook配置
   - 验证Token是否正确
   - 查看Jenkins日志

2. **构建失败**
   - 查看Console Output日志
   - 检查Docker服务状态
   - 验证磁盘空间

3. **服务无法访问**
   - 检查容器状态: `docker ps`
   - 查看容器日志: `docker logs ecom-chatbot-api`
   - 检查端口占用: `sudo lsof -i :8000`

4. **测试超时**
   - 临时跳过测试: Build with Parameters > SKIP_TESTS: true
   - 调整超时时间（在Jenkinsfile中）
   - 使用快速测试套件

### 获取帮助

详细的故障排查指南请查看: [`docs/JENKINS_CICD_GUIDE.md`](docs/JENKINS_CICD_GUIDE.md) 第7章

## 📚 文档索引

| 文档 | 用途 | 适合人群 |
|------|------|----------|
| [`JENKINS_QUICKSTART.md`](docs/JENKINS_QUICKSTART.md) | 5分钟快速开始 | 新手 |
| [`JENKINS_CICD_GUIDE.md`](docs/JENKINS_CICD_GUIDE.md) | 完整使用手册 | 所有人 |
| [`JENKINS_FILES_README.md`](docs/JENKINS_FILES_README.md) | 文件清单说明 | 开发者 |

## 🎓 学习路径

1. **第1天**: 阅读快速开始指南，完成首次部署
2. **第2天**: 阅读完整手册，了解详细配置
3. **第3天**: 实践手动测试，查看各类报告
4. **第4天**: 学习故障排查，熟悉日常维护
5. **第5天**: 优化流水线，配置通知机制

## ⚙️ 配置文件说明

### 生产环境配置

```bash
# 配置文件位置
/opt/ecom-chat-bot/shared/.env.production

# 重要配置项
JWT_SECRET=<自动生成的随机密钥>
DEEPSEEK_API_KEY=<你的API密钥>
CORS_ORIGINS=["http://your-frontend.com"]
```

### Docker编排配置

```bash
# 配置文件
docker-compose.prod.yml

# 主要服务
- api: FastAPI应用服务
- celery-worker: 异步任务处理
```

## 🔒 安全提示

1. **不要提交敏感信息到Git**
   - `.env.production` 已在 `.gitignore` 中
   - 仅使用 `.env.production.template` 作为模板

2. **定期更新密钥**
   - JWT_SECRET
   - API密钥
   - 数据库密码

3. **限制访问权限**
   - Jenkins需要认证
   - 生产配置文件权限设为600
   - 定期审查访问日志

## 🚦 状态说明

| 状态 | 图标 | 说明 |
|------|------|------|
| Success | ✅ | 所有阶段成功 |
| Unstable | ⚠️ | 有测试失败但已部署 |
| Failure | ❌ | 构建失败，未部署 |
| In Progress | ⏳ | 正在执行 |

## 💡 最佳实践

1. **提交前测试**
   ```bash
   # 本地运行测试
   cd backend/tests
   pytest -v
   ```

2. **有意义的commit信息**
   ```bash
   git commit -m "feat: add user authentication"
   git commit -m "fix: resolve database connection issue"
   ```

3. **查看构建状态**
   - 推送代码后，打开Jenkins查看构建进度
   - 关注测试报告，及时修复失败的测试

4. **定期维护**
   - 清理Docker资源
   - 查看磁盘空间
   - 更新依赖版本

## 🎉 总结

现在您的项目拥有了**完整的CI/CD自动化流水线**！

**核心能力**:
- ✅ 代码推送自动部署
- ✅ 完整的自动化测试
- ✅ 零停机滚动更新
- ✅ 自动健康检查
- ✅ 手动测试入口
- ✅ 详细的日志和报告

**下一步**:
1. 阅读 [`docs/JENKINS_QUICKSTART.md`](docs/JENKINS_QUICKSTART.md)
2. 完成首次部署
3. 探索手动测试功能
4. 配置通知机制（可选）

---

**需要帮助？**
- 📖 查看完整手册: [`docs/JENKINS_CICD_GUIDE.md`](docs/JENKINS_CICD_GUIDE.md)
- 🐛 遇到问题: 查看故障排查章节
- 💬 技术支持: 提交Issue

**文档版本**: v1.0  
**最后更新**: 2026-02-12
