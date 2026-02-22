# Jenkins CI/CD 流水线 - 项目文件说明

> 本文档说明Jenkins自动部署流水线相关的所有文件

## 📁 文件清单

### 1. 核心配置文件

#### `Jenkinsfile`
- **用途**: 主CI/CD流水线配置
- **触发**: develop分支代码推送
- **功能**:
  - 自动代码检出
  - 构建Docker镜像
  - 运行完整测试(30-60分钟)
  - 自动部署到生产环境
  - 执行冒烟测试
  - 触发手动测试Job
- **位置**: 项目根目录

#### `Jenkinsfile.manual-test`
- **用途**: 手动测试Job配置
- **触发**: 手动点击或主流水线自动触发
- **功能**:
  - 支持多种测试套件(quick/full/api/integration/smoke)
  - 生成详细测试报告
  - 代码覆盖率报告
- **位置**: 项目根目录

#### `docker-compose.prod.yml`
- **用途**: 生产环境Docker编排配置
- **功能**:
  - 定义API服务配置
  - 定义Celery Worker配置
  - 使用BUILD_NUMBER动态标记版本
- **位置**: 项目根目录
- **部署位置**: `/opt/ecom-chat-bot/docker-compose.prod.yml`

#### `.env.production.template`
- **用途**: 生产环境配置模板
- **功能**:
  - 提供所有必需的环境变量
  - 包含JWT密钥、LLM配置等
- **位置**: 项目根目录
- **实际配置**: `/opt/ecom-chat-bot/shared/.env.production`

### 2. 部署脚本

#### `scripts/jenkins-deploy.sh`
- **用途**: 自动化部署脚本
- **功能**:
  - 滚动更新部署
  - 备份当前版本
  - 健康检查
  - 流量切换
  - 清理旧版本
- **执行**: Jenkins流水线自动调用
- **手动执行**: `bash scripts/jenkins-deploy.sh <BUILD_NUMBER>`

#### `scripts/smoke-test.sh`
- **用途**: 冒烟测试脚本
- **功能**:
  - 验证基础健康检查
  - 测试API文档可访问性
  - 验证核心业务接口
  - 性能测试(响应时间)
  - 容器状态检查
- **执行**: 部署完成后自动运行
- **手动执行**: `bash scripts/smoke-test.sh http://localhost:8000`

#### `scripts/init-deployment.sh`
- **用途**: 服务器环境初始化
- **功能**:
  - 创建部署目录结构
  - 生成生产环境配置
  - 创建Docker网络
  - 配置日志轮转
  - 设置权限
- **执行**: 首次部署前运行一次
- **命令**: `sudo bash scripts/init-deployment.sh`

### 3. 文档

#### `docs/JENKINS_QUICKSTART.md`
- **用途**: 快速开始指南
- **内容**:
  - 5分钟快速配置
  - 3步完成部署
  - 验证安装
  - 常用命令
- **适合**: 新手快速上手

#### `docs/JENKINS_CICD_GUIDE.md`
- **用途**: 完整使用手册
- **内容**:
  - 详细的Jenkins配置说明
  - Git Webhook配置
  - 完整的使用流程
  - 手动测试入口说明
  - 故障排查指南
  - 日常维护手册
  - 常见问题解答
- **适合**: 深入使用和维护

## 🗂️ 目录结构

### 项目目录

```
ecom-chat-bot/
├── Jenkinsfile                          # 主CI/CD流水线
├── Jenkinsfile.manual-test              # 手动测试Job
├── docker-compose.prod.yml              # 生产环境配置
├── .env.production.template             # 环境配置模板
├── scripts/
│   ├── jenkins-deploy.sh                # 部署脚本 ⭐
│   ├── smoke-test.sh                    # 冒烟测试脚本 ⭐
│   └── init-deployment.sh               # 初始化脚本 ⭐
└── docs/
    ├── JENKINS_QUICKSTART.md            # 快速开始 📘
    ├── JENKINS_CICD_GUIDE.md            # 完整手册 📚
    └── JENKINS_FILES_README.md          # 本文档 📄
```

### 服务器目录

```
/opt/ecom-chat-bot/
├── docker-compose.prod.yml              # 生产配置(从项目复制)
├── jenkins-deploy.sh                    # 部署脚本(从项目复制)
├── smoke-test.sh                        # 测试脚本(从项目复制)
├── shared/
│   ├── .env.production                  # 生产环境变量 🔒
│   └── logs/                            # 应用日志
│       ├── api.log
│       └── celery.log
├── releases/                            # 历史版本(未来扩展)
└── backups/                             # 备份文件
```

## 🔄 工作流程

### 自动部署流程

```
1. 开发者推送代码
   git push origin develop

2. Git Webhook触发Jenkins
   → POST http://115.190.75.88:8080/generic-webhook-trigger/invoke

3. Jenkins执行 Jenkinsfile
   ├─ stage: 代码检出
   ├─ stage: 环境检查
   ├─ stage: 构建Docker镜像
   ├─ stage: 运行测试 (30-60min)
   ├─ stage: 测试结果分析
   ├─ stage: 部署到生产环境
   │   └─ 调用 scripts/jenkins-deploy.sh
   ├─ stage: 冒烟测试
   │   └─ 调用 scripts/smoke-test.sh
   └─ stage: 触发手动测试
       └─ 触发 ecom-chatbot-manual-test Job

4. 部署完成，服务更新
   http://115.190.75.88:8000
```

### 手动测试流程

```
1. 用户触发测试
   Jenkins > ecom-chatbot-manual-test > Build with Parameters

2. Jenkins执行 Jenkinsfile.manual-test
   ├─ 准备测试环境
   ├─ 环境检查
   ├─ 构建测试镜像
   ├─ 执行测试 (根据选择的套件)
   ├─ 收集测试报告
   └─ 分析测试结果

3. 查看测试报告
   Jenkins > Build > 测试报告
```

## ⚙️ 配置说明

### Jenkins Job配置

#### 主流水线: `ecom-chatbot-cicd-pipeline`

```yaml
类型: Pipeline
触发器: Generic Webhook Trigger
  Token: ecom-chatbot-deploy-token
  Filter: refs/heads/develop

Pipeline:
  SCM: Git
  Branch: */develop
  Script Path: Jenkinsfile
```

#### 手动测试: `ecom-chatbot-manual-test`

```yaml
类型: Pipeline
触发器: 手动 或 主流水线调用

Pipeline:
  SCM: Git
  Branch: */develop
  Script Path: Jenkinsfile.manual-test
```

### Git Webhook配置

#### Gitee

```
URL: http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token
触发事件: Push
分支过滤: develop
```

#### GitHub

```
Payload URL: http://115.190.75.88:8080/generic-webhook-trigger/invoke?token=ecom-chatbot-deploy-token
Content type: application/json
Events: Push events
```

## 🎯 快速参考

### 常用命令

```bash
# 初始化部署环境(首次运行)
sudo bash scripts/init-deployment.sh

# 手动执行部署
sudo bash scripts/jenkins-deploy.sh <BUILD_NUMBER>

# 手动执行冒烟测试
bash scripts/smoke-test.sh http://localhost:8000

# 查看服务状态
docker ps --filter "name=ecom-chatbot"

# 查看服务日志
docker logs -f ecom-chatbot-api

# 重启服务
docker restart ecom-chatbot-api ecom-chatbot-celery

# 清理Docker资源
docker system prune -a
```

### 常用URL

```
Jenkins平台: http://115.190.75.88:8080
  用户名: zhulang
  密码: hhjy2026@Zl

主流水线: http://115.190.75.88:8080/job/ecom-chatbot-cicd-pipeline/
手动测试: http://115.190.75.88:8080/job/ecom-chatbot-manual-test/

API服务: http://115.190.75.88:8000
健康检查: http://115.190.75.88:8000/health
API文档: http://115.190.75.88:8000/docs
```

## 📖 学习路径

### 第1步: 快速开始 (5分钟)
阅读: [`docs/JENKINS_QUICKSTART.md`](JENKINS_QUICKSTART.md)
- 初始化环境
- 创建Jenkins Job
- 配置Webhook
- 首次部署测试

### 第2步: 深入使用 (30分钟)
阅读: [`docs/JENKINS_CICD_GUIDE.md`](JENKINS_CICD_GUIDE.md)
- 详细配置说明
- 使用流程详解
- 手动测试入口
- 监控和维护

### 第3步: 故障排查 (按需)
查阅: [`docs/JENKINS_CICD_GUIDE.md`](JENKINS_CICD_GUIDE.md) 第7章
- 常见问题解决
- 日志查看方法
- 性能优化建议

## 🔒 安全注意事项

1. **敏感信息保护**
   - `/opt/ecom-chat-bot/shared/.env.production` 权限应为 600
   - 不要将生产配置提交到Git
   - 定期轮换JWT密钥和API密钥

2. **访问控制**
   - Jenkins启用认证
   - Webhook使用Token验证
   - 限制部署目录访问权限

3. **数据备份**
   - 定期备份数据库
   - 保留多个版本镜像
   - 测试恢复流程

## 🆘 获取帮助

遇到问题？按以下顺序寻求帮助:

1. **查看文档**
   - 快速开始: [`JENKINS_QUICKSTART.md`](JENKINS_QUICKSTART.md)
   - 完整手册: [`JENKINS_CICD_GUIDE.md`](JENKINS_CICD_GUIDE.md)

2. **查看日志**
   - Jenkins构建日志
   - Docker容器日志
   - 系统日志

3. **故障排查**
   - 参考故障排查章节
   - 检查服务状态
   - 验证网络连接

4. **提交Issue**
   - 描述问题现象
   - 附上相关日志
   - 说明已尝试的解决方法

---

**文档版本**: v1.0  
**最后更新**: 2026-02-12  
**维护人员**: DevOps Team

**🎉 祝您使用愉快！**
