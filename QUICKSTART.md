# 🚀 快速开始指南

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

### 步骤 2: 克隆项目（如果还没有）

```bash
git clone <repository-url>
cd ecom-chat-bot
```

### 步骤 3: 一键部署

```bash
./deploy.sh
```

**就这么简单！**

脚本会自动完成：
1. ✅ 检查系统依赖
2. ✅ 创建环境变量文件
3. ✅ 构建 Docker 镜像
4. ✅ 启动所有服务（PostgreSQL、Redis、Milvus、RabbitMQ）
5. ✅ 初始化数据库
6. ✅ 创建默认管理员账号
7. ✅ 启动 API 服务

**预计时间**: 5-10 分钟（首次部署）

---

## 🎉 部署成功！

部署完成后，您将看到：

```
╔════════════════════════════════════════════════════════╗
║                  🎉 部署成功！                          ║
╚════════════════════════════════════════════════════════╝

[INFO] 服务访问信息:

  📡 API 服务:
     - 主地址: http://localhost:8000
     - API 文档: http://localhost:8000/docs
     - ReDoc: http://localhost:8000/redoc

  🗄️  数据库服务:
     - PostgreSQL: localhost:5432
       用户名: ecom_user
       密码: ecom_password
       数据库: ecom_chatbot

  🔴 Redis: localhost:6379

  🔍 Milvus: localhost:19530

  🐰 RabbitMQ 管理界面: http://localhost:15672
     用户名: guest
     密码: guest

[INFO] 默认管理员账号:
     用户名: admin
     密码: admin123456
     ⚠️  请立即修改默认密码！
```

---

## 🧪 测试部署

运行快速测试确保一切正常：

```bash
./test.sh
```

您将看到：

```
╔════════════════════════════════════════════════════════╗
║         电商智能客服 SaaS 平台 - 快速测试              ║
╚════════════════════════════════════════════════════════╝

[INFO] 测试 API 健康状态...
[SUCCESS] ✓ API 服务正常

[INFO] 测试管理员登录...
[SUCCESS] ✓ 管理员登录成功

[INFO] 测试获取管理员信息...
[SUCCESS] ✓ 获取管理员信息成功

[INFO] 测试数据库连接...
[SUCCESS] ✓ 数据库连接正常

[INFO] 测试 Redis 连接...
[SUCCESS] ✓ Redis 连接正常

[SUCCESS] 🎉 所有测试通过！部署成功！
```

---

## 📝 第一次使用

### 1. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

您将看到完整的 Swagger UI 文档。

### 2. 管理员登录

在 Swagger UI 中：

1. 找到 `POST /admin/login` 接口
2. 点击 "Try it out"
3. 输入：
   ```json
   {
     "username": "admin",
     "password": "admin123456"
   }
   ```
4. 点击 "Execute"
5. 复制返回的 `access_token`

### 3. 使用 Token 访问其他接口

1. 点击页面右上角的 "Authorize" 按钮
2. 输入：`Bearer <your-token>`
3. 点击 "Authorize"
4. 现在可以测试所有需要认证的接口

### 4. 创建第一个租户

使用 `POST /admin/tenants` 接口创建租户：

```json
{
  "company_name": "测试公司",
  "contact_name": "张三",
  "contact_email": "zhangsan@example.com",
  "contact_phone": "13800138000"
}
```

返回的 `api_key` 就是租户的访问凭证。

---

## 🛠️ 常用管理命令

### 查看服务状态

```bash
./status.sh
```

### 查看日志

```bash
# 查看所有服务日志
./logs.sh

# 查看 API 服务日志
./logs.sh api

# 查看数据库日志
./logs.sh postgres

# 查看 Redis 日志
./logs.sh redis
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启 API 服务
docker-compose restart api
```

### 停止服务

```bash
# 停止服务（保留数据）
./stop.sh
# 然后选择 'N'

# 停止服务并删除所有数据
./stop.sh
# 然后选择 'y'
```

### 重新部署

```bash
# 完全重新部署
./stop.sh  # 选择 'y' 删除数据
./deploy.sh
```

---

## 🔐 安全提示

### ⚠️ 生产环境必做事项

1. **立即修改默认密码**
   - 登录后使用 `PUT /admin/me/password` 修改密码

2. **修改数据库密码**
   - 编辑 `docker-compose.yml`
   - 修改 `POSTGRES_PASSWORD`
   - 重新部署

3. **配置 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

4. **限制端口访问**
   - 只开放 8000 端口（API）
   - 其他端口仅允许内网访问

5. **定期备份数据**
   ```bash
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup.sql
   ```

---

## 🎯 下一步

### 开发建议

1. **阅读完整文档**
   - [README.md](./README.md) - 项目概览
   - [设计方案.md](./docs/设计方案.md) - 详细设计
   - [API文档.md](./docs/API文档.md) - API 使用指南

2. **探索 API**
   - 访问 http://localhost:8000/docs
   - 测试各个接口
   - 了解数据模型

3. **集成到您的系统**
   - 使用 API Key 认证
   - 调用对话接口
   - 管理知识库

### 功能扩展

1. **集成 LLM**
   - 配置 OpenAI API Key
   - 实现对话功能
   - 启用 RAG 检索

2. **添加业务逻辑**
   - 订单查询接口
   - 商品推荐逻辑
   - 客户画像分析

3. **前端开发**
   - 管理后台
   - 客服工作台
   - 数据分析仪表板

---

## ❓ 遇到问题？

### 常见问题

**Q: 端口被占用怎么办？**

A: 修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8001:8000"  # 将 8000 改为其他端口
```

**Q: Milvus 启动失败？**

A: Milvus 需要较多内存（建议 8GB+），可以在 Docker Desktop 中增加内存分配。

**Q: 数据库初始化失败？**

A: 查看日志：
```bash
docker-compose logs db-init
```

**Q: 如何访问数据库？**

A: 使用 PostgreSQL 客户端连接：
```bash
psql -h localhost -U ecom_user -d ecom_chatbot
# 密码: ecom_password
```

### 获取帮助

- 查看详细日志：`./logs.sh <service-name>`
- 查看服务状态：`./status.sh`
- 查看部署文档：[README-DEPLOYMENT.md](./README-DEPLOYMENT.md)
- 查看脚本说明：[docs/部署脚本说明.md](./docs/部署脚本说明.md)

---

## 📊 系统要求

### 最小配置

- CPU: 4 核
- 内存: 8 GB
- 磁盘: 20 GB
- 操作系统: Linux / macOS / Windows (WSL2)

### 推荐配置

- CPU: 8 核
- 内存: 16 GB
- 磁盘: 50 GB
- SSD 硬盘

---

## 🎓 学习资源

- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **SQLAlchemy 文档**: https://docs.sqlalchemy.org/
- **LangChain 文档**: https://python.langchain.com/
- **Milvus 文档**: https://milvus.io/docs

---

## 📞 技术支持

- **GitHub Issues**: 提交问题和建议
- **文档中心**: `/docs` 目录
- **示例代码**: 查看 API 文档中的示例

---

**祝您使用愉快！🎉**

如果觉得有帮助，请给项目一个 ⭐ Star！
