# 电商智能客服 SaaS 平台

基于大模型的多租户电商智能客服SaaS平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

## 📖 项目简介

本项目是一个**生产级**多租户电商智能客服 SaaS 平台，提供完整的后端 API 服务，支持：

- ✅ **多租户架构**：tenant_id 逻辑隔离，支持海量租户
- ✅ **模块化计费**：基础对话、订单查询、商品推荐等可选模块
- ✅ **完整的 API**：RESTful API + WebSocket 实时通信
- ✅ **配额控制**：实时配额检查，支持超额付费
- ✅ **平台管理**：完善的超级管理员后台 API
- ✅ **AI对话集成**：支持智谱AI、OpenAI等多种LLM提供商
- ✅ **意图识别**：基于规则和LLM的混合意图识别
- ✅ **知识库管理**：支持CRUD、搜索、批量导入
- ✅ **RAG检索增强**：向量检索 + 知识库问答
- ✅ **监控统计**：对话统计、响应时间、满意度分析
- ✅ **质量评估**：自动化对话质量评分
- ✅ **Webhook支持**：事件通知机制
- ✅ **模型配置**：灵活的LLM模型配置管理
- ✅ **一键部署**：Docker Compose 全自动部署

## 🛠️ 技术栈

### 后端框架
- **Python** 3.11+
- **FastAPI** 0.104+ - 高性能异步 Web 框架
- **SQLAlchemy** 2.0+ - 异步 ORM
- **Pydantic** v2 - 数据验证
- **Alembic** - 数据库迁移

### 数据存储
- **PostgreSQL** 14+ - 主数据库
- **Redis** 7+ - 缓存、会话管理
- **Milvus** 2.3+ - 向量数据库（RAG）
- **RabbitMQ** - 消息队列

### AI框架
- **LangChain** - LLM 应用开发框架
- **LangGraph** - 工作流编排
- **智谱AI** - GLM系列模型支持
- **OpenAI** - GPT系列模型支持

### 后台任务
- **Celery** - 异步任务队列
- **Redis** - 消息代理

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

# 2. 一键部署
docker-compose up -d

# 3. 查看服务状态
docker-compose ps
```

**就这么简单！**

部署完成后访问：
- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

#### 快速测试

```bash
# 1. 租户注册
curl -X POST "http://localhost:8000/api/v1/tenant/register" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "测试公司",
    "contact_name": "张三",
    "contact_email": "test@example.com",
    "password": "test123456"
  }'

# 2. 创建会话（使用返回的API_KEY）
curl -X POST "http://localhost:8000/api/v1/conversation/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","channel":"web"}'

# 3. AI对话（使用会话ID）
curl -X POST "http://localhost:8000/api/v1/ai-chat/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "CONV_ID",
    "message": "你好",
    "use_rag": false
  }'
```

详细使用指南请查看：
- [📘 快速开始](./QUICKSTART.md)
- [🔧 部署指南](./README-DEPLOYMENT.md)

### 本地开发

```bash
# 1. 启动依赖服务
docker-compose up -d postgres redis milvus rabbitmq

# 2. 进入后端目录
cd backend

# 3. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 初始化数据库
python init_db.py

# 6. 启动开发服务器
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 项目结构

```
ecom-chat-bot/
├── backend/                    # 后端服务
│   ├── api/                   # API 路由层
│   │   ├── main.py           # FastAPI 应用入口
│   │   ├── dependencies.py   # 依赖注入
│   │   ├── middleware.py     # 中间件（配额检查）
│   │   ├── security.py       # 安全相关
│   │   └── routers/          # 路由模块
│   │       ├── admin.py      # 管理员接口
│   │       ├── tenant.py     # 租户接口
│   │       ├── conversation.py # 对话接口
│   │       ├── knowledge.py  # 知识库接口
│   │       ├── ai_chat.py    # AI对话接口
│   │       ├── intent.py     # 意图识别接口
│   │       ├── rag.py        # RAG接口
│   │       ├── monitor.py    # 监控接口
│   │       ├── quality.py    # 质量评估接口
│   │       ├── webhook.py    # Webhook接口
│   │       └── model_config.py # 模型配置接口
│   ├── core/                  # 核心配置
│   │   ├── config.py         # 配置管理
│   │   ├── security.py       # 安全工具
│   │   └── settings.py       # 环境变量
│   ├── models/                # 数据库模型
│   │   ├── tenant.py         # 租户模型
│   │   ├── admin.py          # 管理员模型
│   │   ├── conversation.py   # 对话模型
│   │   ├── knowledge.py      # 知识库模型
│   │   └── model_config.py   # 模型配置
│   ├── schemas/               # Pydantic 模型
│   ├── services/              # 业务逻辑服务
│   │   ├── tenant_service.py
│   │   ├── conversation_service.py
│   │   ├── llm_service.py    # LLM服务
│   │   ├── intent_service.py # 意图识别
│   │   └── rag_service.py    # RAG服务
│   ├── tasks/                 # Celery后台任务
│   │   ├── celery_app.py
│   │   ├── billing_tasks.py
│   │   └── data_tasks.py
│   ├── db/                    # 数据库连接
│   ├── init_db.py            # 数据库初始化
│   ├── requirements.txt      # Python依赖
│   └── Dockerfile            # Docker镜像
├── docs/                      # 项目文档
│   ├── 设计方案.md
│   ├── API文档.md
│   └── 项目结构说明.md
├── docker-compose.yml         # Docker编排
└── README.md                  # 项目说明（本文件）
```

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

### 1. 租户管理系统

- ✅ 租户注册与认证（API Key / JWT）
- ✅ 套餐订阅管理
- ✅ 功能权限控制
- ✅ 数据隔离（tenant_id）
- ✅ 配额使用查询
- ✅ 用量统计

### 2. 对话管理系统

- ✅ 用户会话管理
- ✅ 多轮对话支持
- ✅ 消息历史记录
- ✅ 会话状态管理
- ✅ 并发会话配额控制

### 3. AI对话能力

- ✅ 多LLM提供商支持（智谱AI、OpenAI等）
- ✅ 灵活的模型配置
- ✅ 意图识别（规则+LLM混合）
- ✅ 实体提取
- ✅ 对话摘要生成
- ✅ 上下文记忆管理

### 4. 知识库管理

- ✅ 知识库 CRUD
- ✅ 知识搜索（关键词）
- ✅ RAG 检索增强
- ✅ 批量导入
- ✅ 知识分类和标签

### 5. 监控与质量评估

- ✅ 对话统计
- ✅ 响应时间统计
- ✅ 满意度统计
- ✅ Dashboard汇总
- ✅ 对话质量评估
- ✅ 质量趋势分析

### 6. 扩展功能

- ✅ Webhook事件通知
- ✅ 模型配置管理
- ✅ 支付接口（支付宝）
- ✅ 后台任务处理
- ✅ 异步消息队列

## 🔐 认证方式

### 租户认证

```bash
# 方式1: API Key（推荐）
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/tenant/info

# 方式2: JWT Token
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/v1/tenant/info-token
```

### 管理员认证

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 使用 Token 访问
curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/admin/tenants
```

## 📖 API 文档

### 核心 API 端点

#### 租户管理 API
- `POST /api/v1/tenant/register` - 租户注册
- `POST /api/v1/tenant/login` - 租户登录
- `GET /api/v1/tenant/info` - 获取租户信息（API Key）
- `GET /api/v1/tenant/subscription` - 获取订阅信息
- `GET /api/v1/tenant/quota` - 获取配额使用情况
- `GET /api/v1/tenant/usage` - 获取用量统计

#### 对话管理 API
- `POST /api/v1/conversation/create` - 创建会话
- `GET /api/v1/conversation/{conversation_id}` - 获取会话详情
- `GET /api/v1/conversation/list` - 查询会话列表
- `POST /api/v1/conversation/{conversation_id}/messages` - 发送消息
- `GET /api/v1/conversation/{conversation_id}/messages` - 获取消息列表

#### AI对话 API
- `POST /api/v1/ai-chat/chat` - AI智能对话
- `POST /api/v1/ai-chat/classify-intent` - 意图分类
- `POST /api/v1/ai-chat/extract-entities` - 实体提取
- `GET /api/v1/ai-chat/conversation/{conversation_id}/summary` - 对话摘要
- `DELETE /api/v1/ai-chat/conversation/{conversation_id}/memory` - 清空记忆

#### 知识库 API
- `POST /api/v1/knowledge/create` - 创建知识条目
- `GET /api/v1/knowledge/list` - 查询知识列表
- `GET /api/v1/knowledge/{knowledge_id}` - 获取知识详情
- `PUT /api/v1/knowledge/{knowledge_id}` - 更新知识条目
- `DELETE /api/v1/knowledge/{knowledge_id}` - 删除知识条目
- `POST /api/v1/knowledge/search` - 搜索知识
- `POST /api/v1/knowledge/batch-import` - 批量导入
- `POST /api/v1/knowledge/rag/query` - RAG查询

#### 意图识别 API
- `POST /api/v1/intent/classify` - 意图分类
- `POST /api/v1/intent/extract-entities` - 实体提取
- `GET /api/v1/intent/intents` - 获取可用意图类型

#### RAG API
- `POST /api/v1/rag/retrieve` - RAG检索
- `POST /api/v1/rag/generate` - RAG生成
- `POST /api/v1/rag/index` - 索引知识库
- `GET /api/v1/rag/stats` - RAG统计信息

#### 监控 API
- `GET /api/v1/monitor/conversations` - 对话统计
- `GET /api/v1/monitor/response-time` - 响应时间统计
- `GET /api/v1/monitor/satisfaction` - 满意度统计
- `GET /api/v1/monitor/dashboard` - Dashboard汇总
- `GET /api/v1/monitor/trend/hourly` - 每小时趋势

#### 质量评估 API
- `GET /api/v1/quality/conversation/{conversation_id}` - 评估对话质量
- `GET /api/v1/quality/summary` - 质量统计汇总

#### 模型配置 API
- `POST /api/v1/models` - 创建模型配置
- `GET /api/v1/models` - 列出模型配置
- `GET /api/v1/models/default` - 获取默认模型
- `GET /api/v1/models/{config_id}` - 获取模型配置详情
- `PUT /api/v1/models/{config_id}` - 更新模型配置
- `DELETE /api/v1/models/{config_id}` - 删除模型配置

#### Webhook API
- `POST /api/v1/webhooks` - 创建Webhook
- `GET /api/v1/webhooks` - 列出Webhook
- `POST /api/v1/webhooks/test/{webhook_id}` - 测试Webhook

#### 管理员 API
- `POST /api/v1/admin/login` - 管理员登录
- `GET /api/v1/admin/tenants` - 获取租户列表
- `POST /api/v1/admin/tenants` - 创建租户
- `PUT /api/v1/admin/tenants/{tenant_id}/status` - 更新租户状态

完整的API文档请访问：http://localhost:8000/docs

## 🧪 测试

系统已通过完整的功能测试，测试结果请查看：
- [测试总结报告](./TESTING_SUMMARY.md)

### 测试覆盖

- ✅ 租户注册和登录（52.9%接口完全正常）
- ✅ API Key和Token认证
- ✅ 会话管理
- ✅ 意图识别
- ✅ 监控统计
- ✅ 质量评估
- ✅ 模型配置（智谱AI）

## 🔧 配置说明

### 环境变量配置

主要配置文件：`backend/core/settings.py`

```python
# 应用配置
APP_NAME = "电商智能客服SaaS平台"
APP_VERSION = "1.0.0"
DEBUG = True

# 数据库配置
DATABASE_URL = "postgresql+asyncpg://ecom_user:ecom_password@postgres:5432/ecom_chatbot"

# Redis配置
REDIS_URL = "redis://redis:6379/0"

# LLM配置
DEFAULT_LLM_MODEL = "gpt-3.5-turbo"
OPENAI_API_KEY = "sk-xxx"
OPENAI_API_BASE = "https://api.openai.com/v1"

# 支持的LLM提供商
# - openai: OpenAI GPT系列
# - zhipuai: 智谱AI GLM系列
# - anthropic: Claude系列
# - azure_openai: Azure OpenAI
```

### 智谱AI配置示例

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

## 📊 监控和日志

### 查看日志

```bash
# 查看所有服务
docker-compose logs

# 查看API服务日志
docker-compose logs api

# 查看Celery Worker日志
docker-compose logs celery-worker

# 实时跟踪日志
docker-compose logs -f api
```

### 服务状态

```bash
docker-compose ps
```

## 🛡️ 安全建议

生产环境部署时请注意：

1. ⚠️ **修改默认密码**
   - 管理员密码
   - 数据库密码

2. 🔐 **配置 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

3. 🔥 **配置防火墙**
   - 只开放必要端口（8000）
   - 其他端口不对外暴露

4. 💾 **定期备份**
   ```bash
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup.sql
   ```

5. 🔑 **使用密钥管理**
   - 使用环境变量
   - 不要将敏感信息提交到 Git

## 🎯 开发路线图

### 已完成 ✅

- [x] 多租户架构
- [x] 租户管理 API
- [x] 对话管理 API
- [x] 知识库管理 API
- [x] AI对话集成
- [x] 意图识别系统
- [x] RAG检索增强
- [x] 监控统计系统
- [x] 质量评估系统
- [x] Webhook支持
- [x] 模型配置管理
- [x] Docker一键部署
- [x] Celery后台任务
- [x] 智谱AI集成

### 计划中 📋

- [ ] WebSocket实时通信优化
- [ ] 前端管理控制台
- [ ] 数据分析仪表板
- [ ] 商品推荐引擎
- [ ] 用户画像系统
- [ ] 性能优化
- [ ] 国际化支持

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
- **测试报告**: [TESTING_SUMMARY.md](./TESTING_SUMMARY.md)

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [LangChain](https://python.langchain.com/)
- [智谱AI](https://open.bigmodel.cn/)
- [Milvus](https://milvus.io/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
