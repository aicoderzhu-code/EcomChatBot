# 一键部署指南

本文档介绍如何使用 Docker 一键部署电商智能客服 SaaS 平台。

## 📋 前置要求

### 必需软件

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **操作系统**: Linux / macOS / Windows (WSL2)

### 硬件要求

- **最小配置**:
  - CPU: 4 核
  - 内存: 8 GB
  - 磁盘: 20 GB

- **推荐配置**:
  - CPU: 8 核
  - 内存: 16 GB
  - 磁盘: 50 GB

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd ecom-chat-bot
```

### 2. 配置环境变量（可选）

```bash
# 如果需要自定义配置，编辑 backend/.env 文件
cp backend/.env.example backend/.env
vim backend/.env
```

默认配置已经可以直接使用，但建议修改以下内容：

- `SECRET_KEY`: JWT 密钥
- `OPENAI_API_KEY`: OpenAI API 密钥（如果使用 AI 功能）
- 数据库密码等敏感信息

### 3. 一键部署

```bash
./deploy.sh
```

部署脚本会自动完成以下操作：

1. ✅ 检查系统依赖（Docker、Docker Compose）
2. ✅ 检查并创建环境变量文件
3. ✅ 构建 Docker 镜像
4. ✅ 启动基础服务（PostgreSQL、Redis、Milvus、RabbitMQ）
5. ✅ 等待服务健康检查
6. ✅ 初始化数据库（创建表、创建管理员）
7. ✅ 启动应用服务（API、Celery Worker）
8. ✅ 执行健康检查
9. ✅ 显示访问信息

整个过程大约需要 **5-10 分钟**（取决于网络速度和机器性能）。

## 📡 访问服务

部署成功后，可以通过以下地址访问各项服务：

### API 服务

- **主地址**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 数据库服务

- **PostgreSQL**: `localhost:5432`
  - 数据库: `ecom_chatbot`
  - 用户名: `ecom_user`
  - 密码: `ecom_password`

- **Redis**: `localhost:6379`

- **Milvus**: `localhost:19530`

- **RabbitMQ 管理界面**: http://localhost:15672
  - 用户名: `guest`
  - 密码: `guest`

### 默认管理员账号

- **用户名**: `admin`
- **密码**: `admin123456`

⚠️ **安全提醒**: 请立即修改默认密码！

## 🛠️ 常用命令

我们提供了便捷的管理脚本：

### 查看服务状态

```bash
./status.sh
```

### 查看日志

```bash
# 查看所有服务日志
./logs.sh

# 查看特定服务日志
./logs.sh api          # API 服务
./logs.sh postgres     # 数据库
./logs.sh redis        # Redis
./logs.sh celery-worker # Celery Worker
```

### 停止服务

```bash
# 停止服务（保留数据）
./stop.sh

# 停止服务并删除数据（会提示确认）
./stop.sh
# 然后选择 'y'
```

### 重启服务

```bash
# 使用 docker-compose 命令
docker-compose restart

# 或重启特定服务
docker-compose restart api
```

### 完全重新部署

```bash
# 1. 停止并清理
./stop.sh  # 选择 'y' 删除数据卷

# 2. 重新部署
./deploy.sh
```

## 🔧 手动管理

如果你熟悉 Docker Compose，也可以使用原生命令：

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f [service-name]

# 重启服务
docker-compose restart [service-name]

# 进入容器
docker-compose exec api bash
```

## 📊 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   API    │  │  Celery  │  │ DB Init  │             │
│  │  :8000   │  │  Worker  │  │(一次性)  │             │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘             │
│        │             │              │                   │
│  ┌─────┴─────────────┴──────────────┴─────┐            │
│  │                                         │            │
│  ├─────────────┬─────────────┬────────────┤            │
│  │             │             │            │            │
│  │  PostgreSQL │   Redis     │  RabbitMQ  │            │
│  │   :5432     │   :6379     │  :5672     │            │
│  │             │             │  :15672    │            │
│  └─────────────┴─────────────┴────────────┘            │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │            Milvus (Vector DB)             │          │
│  │  ┌────────┐  ┌────────┐  ┌─────────┐    │          │
│  │  │  etcd  │  │  MinIO │  │ Milvus  │    │          │
│  │  └────────┘  └────────┘  └─────────┘    │          │
│  │                          :19530          │          │
│  └──────────────────────────────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 🔍 故障排查

### 问题 1: 端口被占用

**错误**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**解决方案**:

```bash
# 查找占用端口的进程
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 修改 docker-compose.yml 中的端口映射
# 例如将 "8000:8000" 改为 "8001:8000"
```

### 问题 2: 服务启动超时

**症状**: 基础服务健康检查一直等待

**解决方案**:

```bash
# 1. 查看具体服务日志
./logs.sh postgres
./logs.sh redis

# 2. 增加 Docker 资源限制
# Docker Desktop -> Settings -> Resources
# 调整 CPU 和内存配置

# 3. 重新部署
./stop.sh
./deploy.sh
```

### 问题 3: 数据库初始化失败

**症状**: `db-init` 服务退出失败

**解决方案**:

```bash
# 1. 查看初始化日志
docker-compose logs db-init

# 2. 手动运行初始化
docker-compose run --rm db-init python init_db.py

# 3. 检查数据库连接
docker-compose exec postgres psql -U ecom_user -d ecom_chatbot
```

### 问题 4: Milvus 启动失败

**症状**: Milvus 服务不健康

**解决方案**:

```bash
# Milvus 需要较多资源，确保 Docker 有足够内存
# 至少 4GB 内存

# 如果不需要向量搜索功能，可以暂时注释掉 Milvus
# 编辑 docker-compose.yml，注释掉 milvus 相关服务
```

### 问题 5: 无法访问 API 文档

**症状**: http://localhost:8000/docs 无法访问

**解决方案**:

```bash
# 1. 检查 API 服务状态
docker-compose ps api

# 2. 查看 API 日志
./logs.sh api

# 3. 检查容器健康
docker-compose exec api curl http://localhost:8000/docs

# 4. 重启 API 服务
docker-compose restart api
```

## 🔐 安全建议

### 生产环境部署

1. **修改默认密码**
   ```bash
   # 修改 docker-compose.yml 中的密码
   - POSTGRES_PASSWORD: <strong-password>
   - 管理员密码登录后立即修改
   ```

2. **使用环境变量文件**
   ```bash
   # 不要将 .env 文件提交到 Git
   # 在生产环境使用密钥管理服务
   ```

3. **配置防火墙**
   ```bash
   # 只开放必要的端口（8000）
   # 其他端口（PostgreSQL、Redis 等）不应对外暴露
   ```

4. **启用 HTTPS**
   ```bash
   # 使用 Nginx 反向代理
   # 配置 SSL 证书（Let's Encrypt）
   ```

5. **定期备份**
   ```bash
   # 备份 PostgreSQL 数据
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup.sql
   
   # 备份数据卷
   docker run --rm -v ecom-chat-bot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
   ```

## 📈 性能优化

### 1. 数据库连接池

编辑 `backend/.env`:

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### 2. Redis 缓存

```env
REDIS_MAX_CONNECTIONS=50
CACHE_TTL=3600
```

### 3. Celery Worker

增加 Worker 数量:

```bash
# 编辑 docker-compose.yml
command: celery -A tasks.celery_app worker --loglevel=info --concurrency=4
```

## 🆘 获取帮助

- **查看日志**: `./logs.sh [service-name]`
- **查看状态**: `./status.sh`
- **GitHub Issues**: <repository-url>/issues
- **文档**: `/docs` 目录

## 📝 更新日志

- **v1.0.0** (2026-02-03)
  - ✨ 初始版本
  - ✅ 支持一键部署
  - ✅ 自动数据库初始化
  - ✅ 完整的服务健康检查
