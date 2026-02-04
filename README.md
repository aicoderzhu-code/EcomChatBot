# 电商智能客服 SaaS 平台

基于大模型的 SaaS 化智能客服服务平台（纯后端 API 服务）

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

## 📖 项目简介

本项目是一个多租户电商智能客服 SaaS 平台，提供完整的后端 API 服务，支持：

- ✅ **多租户架构**：tenant_id 逻辑隔离，支持海量租户
- ✅ **模块化计费**：基础对话、订单查询、商品推荐等可选模块
- ✅ **完整的 API**：RESTful API + WebSocket 实时通信
- ✅ **配额控制**：实时配额检查，支持超额付费
- ✅ **平台管理**：完善的超级管理员后台 API
- ✅ **一键部署**：Docker Compose 全自动部署
- ⏳ **LangChain + LangGraph**：对话流程编排（框架已实现）
- ⏳ **RAG 检索增强**：Milvus 向量数据库（框架已实现）

## 🛠️ 技术栈

### 后端框架
- **Python** 3.11+
- **FastAPI** - 高性能异步 Web 框架
- **SQLAlchemy 2.0** - 异步 ORM
- **Pydantic v2** - 数据验证
- **Alembic** - 数据库迁移

### 数据存储
- **PostgreSQL** 14+ - 主数据库
- **Redis** - 缓存、会话管理
- **Milvus** 2.3+ - 向量数据库（RAG）
- **RabbitMQ** - 消息队列

### 大模型框架（待集成）
- **LangChain** - LLM 应用开发框架
- **LangGraph** - 工作流编排

## 🚀 快速开始

### 一键部署（推荐）

#### 前置要求

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **操作系统**: Linux / macOS / Windows (WSL2)
- **硬件要求**: CPU 4核+ / 内存 8GB+ / 磁盘 20GB+

#### 部署步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd ecom-chat-bot

# 2. 一键部署（包含所有服务和数据库初始化）
./deploy.sh
```

就这么简单！脚本会自动完成：
- ✅ 检查系统依赖
- ✅ 构建 Docker 镜像  
- ✅ 启动所有服务（PostgreSQL、Redis、Milvus、RabbitMQ）
- ✅ 初始化数据库和创建管理员账号
- ✅ 启动 API 服务和 Celery Worker

部署完成后访问：
- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **默认管理员**: `admin` / `admin123456` ⚠️ 请立即修改密码

#### 常用命令

```bash
./status.sh    # 查看服务状态
./logs.sh      # 查看所有服务日志
./logs.sh api  # 查看 API 服务日志
./test.sh      # 测试部署是否成功
./stop.sh      # 停止服务
```

详细部署文档请查看：
- [📘 一键部署指南](./README-DEPLOYMENT.md)
- [🔧 部署脚本说明](./docs/部署脚本说明.md)

### 本地开发（不使用 Docker）

如果你想在本地直接运行（需要手动安装并启动 PostgreSQL、Redis 等）：

```bash
# 1. 启动依赖服务（使用 Docker）
docker-compose up -d postgres redis milvus rabbitmq

# 2. 进入后端目录
cd backend

# 3. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接等

# 6. 初始化数据库
python init_db.py

# 7. 启动开发服务器
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 项目结构

```
ecom-chat-bot/
├── backend/                  # 后端服务
│   ├── api/                 # API 路由
│   │   ├── main.py         # FastAPI 应用入口
│   │   ├── dependencies.py # 依赖注入
│   │   └── routers/        # 路由模块
│   ├── core/               # 核心配置
│   ├── models/             # 数据库模型
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 业务逻辑服务
│   ├── db/                 # 数据库连接
│   ├── migrations/         # Alembic 迁移
│   ├── init_db.py          # 数据库初始化脚本
│   ├── requirements.txt    # Python 依赖
│   ├── Dockerfile         # Docker 镜像
│   └── .env.example       # 环境变量示例
├── docs/                    # 项目文档
│   ├── 设计方案.md         # 详细设计方案
│   ├── API文档.md          # API 接口文档
│   ├── 项目结构说明.md     # 项目结构说明
│   └── 部署脚本说明.md     # 部署脚本使用说明
├── scripts/                 # 工具脚本
│   └── quick_start.sh      # 快速启动脚本（旧版）
├── deploy.sh               # 一键部署脚本
├── stop.sh                 # 停止服务脚本
├── logs.sh                 # 日志查看脚本
├── status.sh               # 状态检查脚本
├── test.sh                 # 快速测试脚本
├── docker-compose.yml      # Docker Compose 编排
├── .dockerignore           # Docker 忽略文件
├── .gitignore              # Git 忽略配置
└── README.md               # 项目说明（本文件）
```

详细结构说明：[项目结构文档](./docs/项目结构说明.md)

## 📡 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| API 服务 | 8000 | FastAPI 应用 |
| PostgreSQL | 5432 | 主数据库 |
| Redis | 6379 | 缓存 |
| Milvus | 19530 | 向量数据库 |
| RabbitMQ | 5672 | 消息队列 |
| RabbitMQ 管理 | 15672 | 管理界面 (guest/guest) |

## 📚 核心功能

### 1. 租户管理

- 租户注册与认证（API Key / JWT）
- 套餐订阅管理
- 功能权限控制
- 数据隔离（tenant_id）

### 2. 对话管理

- 用户会话管理
- 多轮对话支持
- 消息历史记录
- WebSocket 实时通信（框架已实现）

### 3. 知识库管理

- 知识库 CRUD
- 知识搜索（关键词 + 向量检索）
- RAG 检索增强（框架已实现）
- 批量导入

### 4. 计费系统

- 模块化定价（对话、查询、推荐、分析）
- 用量统计（对话次数、Token 消耗）
- 配额控制与监控
- 账单生成与支付

### 5. 平台管理

- 租户列表与搜索
- 套餐分配与管理
- 配额调整
- 操作审计日志
- 财务数据统计

## 🔐 认证方式

### 租户认证

```bash
# 方式1: API Key（推荐）
curl -H "X-API-Key: your-api-key" http://localhost:8000/tenant/me

# 方式2: JWT Token
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/tenant/me
```

### 管理员认证

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123456"}'

# 使用 Token 访问
curl -H "Authorization: Bearer {token}" http://localhost:8000/admin/tenants
```

## 📖 API 文档

部署成功后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **详细文档**: [API文档.md](./docs/API文档.md)

### 主要 API 端点

#### 管理员 API

- `POST /admin/login` - 管理员登录
- `GET /admin/me` - 获取当前管理员信息
- `GET /admin/tenants` - 获取租户列表
- `POST /admin/tenants` - 创建租户
- `PUT /admin/tenants/{tenant_id}/subscription` - 分配套餐
- `POST /admin/tenants/{tenant_id}/quota/adjust` - 调整配额

#### 租户 API

- `GET /tenant/me` - 获取租户信息
- `GET /tenant/subscription` - 获取订阅信息
- `GET /tenant/usage` - 获取用量统计
- `GET /tenant/quota` - 获取配额信息

#### 对话 API

- `POST /conversations` - 创建会话
- `POST /conversations/{conversation_id}/messages` - 发送消息
- `GET /conversations/{conversation_id}` - 获取会话详情
- `GET /conversations/{conversation_id}/messages` - 获取消息列表

#### 知识库 API

- `POST /knowledge` - 创建知识条目
- `GET /knowledge` - 列出知识库
- `POST /knowledge/search` - 搜索知识
- `POST /knowledge/rag` - RAG 查询
- `POST /knowledge/batch-import` - 批量导入

## 🧪 测试

```bash
# 运行测试
cd backend
pytest

# 查看测试覆盖率
pytest --cov=. --cov-report=html
```

## 🔧 数据库管理

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 📊 监控和日志

### 查看日志

```bash
# 所有服务
./logs.sh

# 特定服务
./logs.sh api
./logs.sh postgres
./logs.sh redis
```

### 服务状态

```bash
./status.sh
```

## 🛡️ 安全建议

生产环境部署时请注意：

1. ⚠️ **修改默认密码**
   - 管理员密码：登录后立即修改
   - 数据库密码：编辑 `docker-compose.yml`

2. 🔐 **配置 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书（Let's Encrypt）

3. 🔥 **配置防火墙**
   - 只开放必要端口（8000）
   - 其他端口不对外暴露

4. 💾 **定期备份**
   ```bash
   # 备份数据库
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup.sql
   ```

5. 🔑 **使用密钥管理**
   - 使用环境变量或密钥管理服务
   - 不要将敏感信息提交到 Git

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- **项目文档**: [./docs](./docs)
- **问题反馈**: GitHub Issues
- **设计方案**: [设计方案.md](./docs/设计方案.md)

## 🎯 开发路线图

### 已完成 ✅

- [x] 多租户架构
- [x] 租户管理 API
- [x] 对话管理 API
- [x] 知识库管理 API
- [x] 计费系统
- [x] 平台管理后台
- [x] 数据库初始化
- [x] Docker 一键部署
- [x] API 文档
- [x] 基础安全认证

### 进行中 🚧

- [ ] LangChain 集成
- [ ] LangGraph 工作流编排
- [ ] Milvus 向量检索
- [ ] WebSocket 实时通信
- [ ] 单元测试和集成测试

### 计划中 📋

- [ ] 前端管理控制台
- [ ] 数据分析仪表板
- [ ] 用户画像系统
- [ ] 商品推荐引擎
- [ ] Webhook 事件通知
- [ ] 监控和告警
- [ ] 性能优化
- [ ] 国际化支持

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [LangChain](https://python.langchain.com/)
- [Milvus](https://milvus.io/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
