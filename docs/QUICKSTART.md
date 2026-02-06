# 🚀 快速开始指南

> **5分钟快速部署并使用电商智能客服SaaS平台**

## 一键部署 - 3 步完成

### 步骤 1: 确保安装 Docker

```bash
# 检查 Docker 是否已安装
docker --version
docker-compose --version
```

如果未安装，请访问：
- **Mac**: https://docs.docker.com/desktop/install/mac-install/
- **Windows**: https://docs.docker.com/desktop/install/windows-install/
- **Linux**: https://docs.docker.com/engine/install/

### 步骤 2: 克隆项目

```bash
git clone <repository-url>
cd ecom-chat-bot
```

### 步骤 3: 启动服务

```bash
docker-compose up -d
```

**就这么简单！**

启动命令会自动完成：
1. ✅ 拉取Docker镜像
2. ✅ 启动所有服务（PostgreSQL、Redis、Milvus、RabbitMQ）
3. ✅ 初始化数据库
4. ✅ 启动 API 服务和Celery Worker

**预计时间**: 3-5 分钟（首次部署需要拉取镜像）

---

## 🎉 验证部署

### 检查服务状态

```bash
docker-compose ps
```

所有服务应该显示为 `Up` 状态。

### 健康检查

```bash
curl http://localhost:8000/health
```

预期返回：
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 📝 快速开始使用

### 1. 注册租户

```bash
curl -X POST "http://localhost:8000/api/v1/tenant/register" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "我的测试公司",
    "contact_name": "张三",
    "contact_email": "test@example.com",
    "contact_phone": "13800138000",
    "password": "test123456"
  }'
```

响应示例：
```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant_xxx",
    "api_key": "eck_xxx",
    "message": "注册成功，请妥善保存API Key"
  }
}
```

**⚠️ 重要**: 请保存返回的 `api_key`，后续所有API调用都需要使用！

### 2. 登录获取Token

```bash
curl -X POST "http://localhost:8000/api/v1/tenant/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }'
```

响应示例：
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 86400,
    "tenant_id": "tenant_xxx"
  }
}
```

### 3. 创建会话

使用刚才获取的 `api_key`：

```bash
curl -X POST "http://localhost:8000/api/v1/conversation/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "channel": "web"
  }'
```

响应示例：
```json
{
  "success": true,
  "data": {
    "conversation_id": "conv_xxx",
    "user_id": "user123",
    "status": "active",
    "created_at": "2026-02-05T10:00:00"
  }
}
```

### 4. AI对话

使用返回的 `conversation_id`：

```bash
curl -X POST "http://localhost:8000/api/v1/ai-chat/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_xxx",
    "message": "你好，请介绍一下你自己",
    "use_rag": false
  }'
```

响应示例：
```json
{
  "success": true,
  "data": {
    "response": "你好！我是一个智能客服助手...",
    "conversation_id": "conv_xxx",
    "total_tokens": 150,
    "model": "glm-4-flash"
  }
}
```

---

## 🔧 配置智谱AI（推荐）

系统默认使用OpenAI配置，建议配置智谱AI：

```bash
# 创建智谱AI模型配置
curl -X POST "http://localhost:8000/api/v1/models" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "zhipuai",
    "model_name": "glm-4-flash",
    "api_key": "YOUR_ZHIPUAI_API_KEY",
    "api_base": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "temperature": 0.7,
    "max_tokens": 2000,
    "use_case": "chat",
    "is_default": true
  }'
```

获取智谱AI API Key: https://open.bigmodel.cn/

---

## 📖 访问API文档

### Swagger UI（推荐）

打开浏览器访问：http://localhost:8000/docs

在Swagger UI中可以：
- 📖 查看所有API接口
- 🧪 在线测试接口
- 📝 查看请求/响应示例
- 🔐 配置认证Token

### ReDoc

访问：http://localhost:8000/redoc

---

## 🧪 更多测试示例

### 创建知识库条目

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_type": "faq",
    "title": "如何退款？",
    "content": "用户可以在订单详情页申请退款，退款将在1-3个工作日内原路返回。",
    "category": "售后",
    "tags": ["退款", "售后"],
    "priority": 1
  }'
```

### 意图识别

```bash
curl -X POST "http://localhost:8000/api/v1/intent/classify" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我要退款",
    "use_llm": false
  }'
```

响应：
```json
{
  "success": true,
  "data": {
    "intent": "AFTER_SALES",
    "confidence": "medium",
    "score": 0.8,
    "method": "rule"
  }
}
```

### 查看监控统计

```bash
curl -X GET "http://localhost:8000/api/v1/monitor/dashboard?time_range=24h" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## 🛠️ 常用管理命令

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看API服务日志
docker-compose logs api

# 实时跟踪日志
docker-compose logs -f api
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启API服务
docker-compose restart api
```

### 停止服务

```bash
# 停止所有服务（保留数据）
docker-compose down

# 停止并删除所有数据
docker-compose down -v
```

---

## 🔐 安全提示

### ⚠️ 生产环境必做事项

1. **修改默认密码**
   ```yaml
   # 编辑 docker-compose.yml
   environment:
     POSTGRES_PASSWORD: your-secure-password
   ```

2. **限制端口访问**
   - 只开放 8000 端口（API）
   - 其他端口仅允许内网访问

3. **配置HTTPS**
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8000;
       }
   }
   ```

4. **定期备份数据**
   ```bash
   # 备份数据库
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup_$(date +%Y%m%d).sql
   ```

---

## 🎯 下一步

### 推荐阅读

1. **完整README** - [README.md](./README.md)
   - 技术栈详解
   - 完整API列表
   - 架构设计

2. **测试报告** - [TESTING_SUMMARY.md](./TESTING_SUMMARY.md)
   - 接口测试结果
   - 已修复问题
   - 待优化项

3. **功能清单** - [功能实现清单.md](./功能实现清单.md)
   - 详细功能列表
   - 实现状态
   - 开发路线图

### 集成建议

1. **Web应用集成**
   - 使用API Key认证
   - 调用对话接口
   - 管理会话和用户

2. **移动端集成**
   - RESTful API调用
   - WebSocket实时通信
   - 推送通知

3. **第三方系统集成**
   - Webhook事件通知
   - 统一认证
   - 数据同步

---

## ❓ 常见问题

### Q: 端口被占用怎么办？

A: 修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8001:8000"  # 将8000改为其他端口
```

### Q: 如何查看数据库数据？

A: 使用PostgreSQL客户端连接：
```bash
psql -h localhost -U ecom_user -d ecom_chatbot
# 密码: ecom_password
```

### Q: 如何重置数据库？

A:
```bash
# 停止服务
docker-compose down -v

# 重新启动
docker-compose up -d
```

### Q: AI对话失败怎么办？

A: 检查以下几点：
1. 确认已配置模型API Key
2. 查看API服务日志：`docker-compose logs api`
3. 验证API Key是否有效

---

## 📊 系统要求

### 最小配置

- CPU: 4 核
- 内存: 8 GB
- 磁盘: 20 GB

### 推荐配置

- CPU: 8 核
- 内存: 16 GB
- 磁盘: 50 GB SSD

---

## 🎓 学习资源

- **FastAPI文档**: https://fastapi.tiangolo.com/
- **智谱AI文档**: https://open.bigmodel.cn/dev/api
- **LangChain文档**: https://python.langchain.com/

---

## 📞 获取帮助

- **API文档**: http://localhost:8000/docs
- **完整README**: [README.md](./README.md)
- **部署指南**: [README-DEPLOYMENT.md](./README-DEPLOYMENT.md)

---

**祝您使用愉快！🎉**

如果觉得有帮助，请给项目一个 ⭐ Star！
