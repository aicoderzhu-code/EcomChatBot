<div align="center">
  <img src="./frontend/public/logos/logo.svg" alt="EcomChat Logo" width="200"/>

  # 电商智能客服 & AI 内容生成 SaaS 平台

  基于大模型的多租户电商 SaaS 平台，集智能客服、AI 内容生成、商品管理、智能定价于一体，提供完整的前后端解决方案。
</div>

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

## 📖 项目简介

本项目是一个**生产级**多租户电商智能客服 SaaS 平台，包含完整的前后端实现：

- **用户端（租户工作台）**：AI 对话、商品管理、AI 内容生成（海报/视频/文案）、知识库、智能定价、订单分析、订阅支付
- **管理后台（超管后台）**：租户管理、订阅计费、平台统计、审计日志、平台配置

核心能力：

- ✅ **多租户架构**：`tenant_id` 逻辑隔离，支持海量租户接入
- ✅ **AI 模型集成**：基于火山引擎提供的 LLM、Embedding、图像生成、视频生成模型
- ✅ **AI 内容生成**：海报（图像）生成、短视频生成、商品标题 & 描述文案生成
- ✅ **商品管理**：电商平台商品同步（全量/增量）、商品提示词管理、生命周期管理
- ✅ **智能定价**：竞品监控、多策略定价分析（竞争/高端/渗透/动态）、AI 定价建议
- ✅ **订单分析**：订单同步、热销商品排行、买家统计、AI 分析报告
- ✅ **平台对接**：拼多多 OAuth 授权、Webhook 消息接收、自动回复与人工接管
- ✅ **RAG 检索增强**：Milvus 向量数据库 + 知识库语义检索 + 重排序
- ✅ **意图识别**：规则 + LLM 混合意图识别与实体提取
- ✅ **实时对话**：WebSocket 全双工通信与流式响应
- ✅ **LLM Playground**：模型测试沙盒，支持自定义 System Prompt、RAG 开关、Token 统计
- ✅ **对象存储**：MinIO 存储生成素材，支持下载与一键上传至电商平台
- ✅ **订阅与支付**：支付宝、微信支付集成，支持套餐升降级与发票
- ✅ **灵活认证**：API Key（对外服务）+ JWT Token（管理后台）双认证
- ✅ **监控与质量评估**：对话统计、响应时间、满意度、质量自动评分
- ✅ **Webhook 通知**：事件驱动的外部系统集成
- ✅ **安全审计**：完善的操作审计日志与敏感词过滤
- ✅ **一键部署**：Docker Compose 全自动编排

## 🛠️ 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| 框架 | FastAPI 0.109、Uvicorn（ASGI） |
| ORM | SQLAlchemy 2.0（异步） |
| 数据验证 | Pydantic v2 |
| AI 框架 | LangChain 0.1、LangGraph、Sentence Transformers |
| AI 模型服务 | 火山引擎（LLM、Embedding、图像生成、视频生成） |
| 后台任务 | Celery 5.3 + Flower 监控界面 |
| 消息队列 | RabbitMQ（任务分发）、Redis（Broker/Result） |
| WebSocket | FastAPI WebSocket |

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 14（App Router）、React 18、TypeScript |
| UI 组件库 | Ant Design 6、@ant-design/charts |
| 状态管理 | Zustand 5 |
| HTTP 客户端 | Axios |
| 样式 | Tailwind CSS 3 |
| E2E 测试 | Playwright |

### 数据存储

| 组件 | 用途 |
|------|------|
| PostgreSQL 14+ | 主关系数据库 |
| Redis 7+ | 缓存、会话、Celery Broker |
| Milvus 2.3+ | 向量数据库（RAG 检索） |
| MinIO | 对象存储（生成素材持久化 & Milvus 依赖） |
| RabbitMQ | 异步任务消息队列 |

### 运维

- **反向代理**：Nginx
- **容器化**：Docker + Docker Compose（开发 & 生产两套配置）
- **CI/CD**：Jenkins Pipeline + GitHub Actions
- **监控**：Prometheus 指标采集、Sentry 错误追踪、Flower 任务监控

## 🚀 快速开始

### 前置要求

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **操作系统**：Linux / macOS / Windows（WSL2）
- **硬件**：CPU 4 核+ / 内存 8GB+ / 磁盘 20GB+

### 一键部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd ecom-chat-bot

# 2. 一键启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps
```

部署完成后访问：

| 地址 | 说明 |
|------|------|
| http://localhost/login | 用户端（租户工作台） |
| http://localhost/admin-login | 管理后台（超管后台） |
| http://localhost:8000/docs | 后端 API 文档（Swagger UI） |
| http://localhost:8000/health | 健康检查 |
| http://localhost:9001 | MinIO Console（minioadmin/minioadmin） |
| http://localhost:15672 | RabbitMQ 管理界面（guest/guest） |

### 快速验证

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

# 2. 创建会话（使用注册返回的 API Key）
curl -X POST "http://localhost:8000/api/v1/conversation/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "channel": "web"}'

# 3. 发起 AI 对话
curl -X POST "http://localhost:8000/api/v1/ai-chat/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "CONV_ID",
    "message": "你好，我想查一下我的订单",
    "use_rag": false
  }'

# 4. 超级管理员登录（默认账号: admin / admin123456）
curl -X POST "http://localhost:8000/api/v1/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123456"}'
```

### 本地开发

```bash
# 启动依赖服务
docker-compose up -d postgres redis milvus rabbitmq

# ── 后端 ──────────────��───────────────
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py              # 初始化数据库 & 创建默认超管
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── 前端（新终端）────────────────────
cd frontend
npm install
npm run dev                    # 访问 http://localhost:3000
```

### 数据库初始化说明

本项目使用 `init_db.py` 进行数据库初始化，**不需要运行数据库迁移**：

- **自动建表**：`init_db.py` 使用 SQLAlchemy 的 `Base.metadata.create_all()` 自动创建所有 47 张表
- **初始数据**：自动创建默认超级管理员（admin/admin123456）、系统内容模板、平台媒体规范
- **幂等性**：可重复运行，已存在的数据不会重复创建
- **Docker 部署**：`db-init` 容器会在启动时自动运行 `init_db.py`

**重新部署时**：
```bash
# 完全清空数据库重新初始化
docker compose down -v  # 删除所有容器和数据卷
docker compose up -d    # 重新启动，自动初始化数据库
```

详细部署说明：[快速开始指南](./docs/QUICKSTART.md) | [生产部署指南](./docs/README-DEPLOYMENT.md) | [域名部署指南](./docs/DEPLOYMENT.md) | [Jenkins CI/CD](./docs/JENKINS_SETUP.md)

### 域名部署（HTTPS）

如果您已有域名并完成备案，可以使用以下命令快速部署 HTTPS 服务：

```bash
# 1. 获取 SSL 证书
sudo ./scripts/get-ssl-cert.sh

# 2. 部署应用
sudo ./scripts/deploy-domain.sh
```

详细说明：[域名部署指南](./docs/DEPLOYMENT.md) | [快速参考](./docs/DEPLOYMENT_QUICK_REF.md)

## 📁 项目结构

```
ecom-chat-bot/
├── backend/                    # FastAPI 后端
│   ├── api/
│   │   ├── main.py            # 应用入口
│   │   ├── dependencies.py    # 依赖注入（认证、DB）
│   │   ├── middleware/        # 配额检查、限流、日志中间件
│   │   └── routers/           # 路由模块（29 个）
│   ├── core/                  # 核心配置（config、security、permissions、exceptions）
│   ├── models/                # SQLAlchemy ORM 模型（20 个）
│   ├── schemas/               # Pydantic 请求/响应模型（20+ 个）
│   ├── services/              # 业务逻辑层（50+ 服务）
│   ├── tasks/                 # Celery 后台任务（计费、通知、Webhook、内容生成、商品同步）
│   ├── db/                    # 数据库工具（session、redis、RLS）
│   ├── migrations/            # Alembic 数据库迁移
│   ├── tests/                 # 测试套件
│   ├── init_db.py             # 数据库初始化脚本
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # Next.js 14 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/        # 登录 / 注册
│   │   │   ├── (dashboard)/   # 用户端（租户工作台）
│   │   │   │   ├── dashboard/ # 概览
│   │   │   │   ├── chat/      # AI 对话界面
│   │   │   │   ├── products/  # 商品管理
│   │   │   │   ├── content/   # AI 内容生成（海报/视频/素材/提示词）
│   │   │   │   ├── knowledge/ # 知识库管理
│   │   │   │   ├── pricing/   # 智能定价
│   │   │   │   ├── analytics/ # 数据分析（订单/报告）
│   │   │   │   └── settings/  # 租户设置
│   │   │   └── (admin)/       # 管理后台（超管）
│   │   │       ├── admins/    # 管理员账号管理
│   │   │       ├── tenants/   # 租户管理
│   │   │       ├── subscriptions/ # 订阅管理
│   │   │       ├── payments/  # 支付 & 账单
│   │   │       ├── statistics/# 平台统计
│   │   │       ├── platform/  # 平台配置
│   │   │       └── audit/     # 审计日志
│   │   ├── components/        # 复用组件
│   │   ├── store/             # Zustand 状态管理
│   │   ├── lib/api/           # API 客户端
│   │   └── types/             # TypeScript 类型定义
│   ├── e2e/                   # Playwright E2E 测试
│   └── Dockerfile
├── nginx/                     # Nginx 反向代理配置
├── docs/                      # 项目文档
├── scripts/                   # 部署 & 工具脚本
├── docker-compose.yml         # 开发环境编排
├── docker-compose.prod.yml    # 生产环境编排
├── Jenkinsfile                # Jenkins CI/CD
└── run_all_tests.sh           # 完整测试入口
```

## 👤 用户端（租户工作台）

用户端面向各电商租户，提供 AI 客服、内容生成、商品管理等能力的接入与管理。访问地址：`http://localhost/login`

### 1. 注册与登录

- **租户注册**：填写公司名称、联系人、邮箱、密码完成注册，系统自动分配 API Key
- **租户登录**：邮箱 + 密码登录，获取 JWT Token 用于后续操作
- **认证方式**：
  - `X-API-Key`：用于服务端集成（推荐）
  - `Authorization: Bearer <token>`：用于前端登录态

```bash
# API Key 认证
curl -H "X-API-Key: eck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  http://localhost:8000/api/v1/tenant/info

# JWT Token 认证
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/api/v1/tenant/info-token
```

### 2. 工作台概览（Dashboard）

- 核心指标展示：今日对话数、累计用量、剩余配额
- 近期对话列表：快速查看最新会话记录
- 快捷入口：跳转至对话、知识库、设置等功能模块

### 3. AI 对话

- **实时对话**：基于 WebSocket 的全双工通信，支持流式响应
- **多轮上下文**：自动维护对话历史，支持多轮摘要压缩
- **意图识别**：规则 + LLM 混合识别用户意图（订单查询、商品推荐、售后等）
- **RAG 增强**：可选开启知识库检索，结合向量语义搜索与重排序提升回答质量
- **对话管理**：查看历史会话、消息反馈、会话状态管理

```bash
# 创建会话
curl -X POST "http://localhost:8000/api/v1/conversation/create" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"user_id": "user123", "channel": "web"}'

# 发起 AI 对话（HTTP）
curl -X POST "http://localhost:8000/api/v1/ai-chat/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"conversation_id": "CONV_ID", "message": "查询订单状态", "use_rag": true}'

# WebSocket 实时对话
# ws://localhost:8000/api/v1/ws/chat?api_key=YOUR_API_KEY
```

### 4. 知识库管理

- **知识条目 CRUD**：新增、编辑、删除知识条目，支持关键词搜索
- **批量导入**：支持批量上传知识内容
- **向量化索引**：基于 Sentence Transformers 自动生成向量，存入 Milvus
- **语义检索**：支持语义相似度搜索，可选择嵌入模型与重排模型
- **使用追踪**：记录每条知识的引用次数与使用日志

### 5. 商品管理

- **商品列表**：展示商品图片、标题、价格、销量、库存、上下架状态
- **商品搜索**：按关键词、状态筛选商品
- **平台同步**：支持全量同步与增量同步，从电商平台拉取商品数据
- **同步任务管理**：查看同步进度、任务状态、错误日志
- **定时同步调度**：配置自动同步频率，保持商品数据实时更新
- **商品提示词**：为每个商品配置图片、视频、标题、描述的生成提示词

```bash
# 触发商品全量同步
curl -X POST "http://localhost:8000/api/v1/products/sync" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"sync_type": "full"}'

# 获取商品列表
curl "http://localhost:8000/api/v1/products" \
  -H "X-API-Key: YOUR_API_KEY"
```

### 6. AI 内容生成

基于火山引擎的 AI 内容生成系统，支持海报、视频、文案的一站式生成与管理。

#### 海报生成（图像）

- **商品关联**：选择商品并使用其提示词生成海报
- **火山引擎模型**：使用 doubao-seedream 系列模型生成高质量图像
- **参数配置**：图片尺寸、批量数量等参数
- **批量生成**：单次可生成多张图片
- **任务跟踪**：异步生成，实时查看任务状态与进度

#### 视频生成

- **文生视频 / 图生视频**：支持纯文本描述或参考图片生成视频
- **火山引擎模型**：使用 doubao-seedance 系列模型生成视频
- **参数配置**：视频时长等参数
- **任务跟踪**：异步生成，实时查看任务状态

#### 素材库

- **统一管理**：图片、视频、文案素材集中管理
- **筛选与搜索**：按类型、收藏状态、关键词筛选
- **素材操作**：预览、下载、收藏标记、删除
- **平台上传**：一键将素材上传至电商平台

#### 提示词管理

- **提示词 CRUD**：创建、编辑、删除商品提示词
- **类型分类**：图片生成、视频生成、标题生成、描述生成
- **使用统计**：记录每条提示词的使用次数

```bash
# 创建海报生成任务
curl -X POST "http://localhost:8000/api/v1/content/generate" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "product_id": "PRODUCT_ID",
    "generation_type": "poster",
    "prompt": "高端电商产品海报，白色背景"
  }'
```

### 7. 智能定价

- **竞品管理**：添加、查看、删除竞品商品数据
- **多策略分析**：支持竞争定价、高端定价、渗透定价、动态定价四种策略
- **AI 定价建议**：基于竞品数据与市场分析，生成最低价、最高价、建议价
- **分析历史**：追踪历史定价分析记录
- **AI 摘要**：自动生成定价分析摘要与建议说明

```bash
# 执行定价分析
curl -X POST "http://localhost:8000/api/v1/pricing/analyze" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "product_id": "PRODUCT_ID",
    "strategy": "competitive"
  }'
```

### 8. 订单分析

- **订单同步**：从电商平台同步订单数据
- **订单列表**：查看订单详情，支持筛选与搜索
- **分析概览**：订单总量、销售额、平均客单价等核心指标
- **热销排行**：热销商品排行榜
- **买家统计**：买家购买频次、消费金额分析
- **分析报告**：AI 生成日/周/月/自定义周期分析报告

### 9. 设置

#### 平台对接（拼多多）

- **OAuth 授权**：配置 App Key/Secret，完成拼多多平台授权
- **Webhook 接收**：接收平台消息推送，支持验签
- **自动回复**：AI 自动回复买家消息，可配置置信度阈值
- **人工接管**：低置信度时自动转人工，支持自定义转人工提示语
- **连接管理**：查看平台连接状态，管理授权信息

#### Webhook 配置

- 订阅平台事件（对话创建、消息发送、配额告警等）
- 配置回调 URL，支持自定义 Header 与签名验证
- 提供 Webhook 测试功能，验证接收端可用性

#### API Key 管理

- 查看当前 API Key
- 重新生成 API Key（旧 Key 立即失效）

### 11. 订阅与支付

- **套餐选择**：按功能模块计费（基础对话、订单查询、商品推荐等）
- **实时配额**：Redis 实时扣减配额，支持超额付费
- **支付方式**：支付宝、微信支付
- **套餐升降级**：按比例计算剩余费用，无缝切换套餐
- **发票管理**：申请、查看、下载电子发票

## 🔧 管理后台（超管后台）

管理后台面向平台运营人员，提供全平台的租户管理、计费运营与监控能力。

访问地址：`http://localhost/admin-login`，默认账号：`admin / admin123456`

> **安全提示**：生产环境请立即修改默认密码。

### 1. 管理员登录与权限

支持 RBAC 四级权限体系：

| 角色 | 说明 |
|------|------|
| SUPER_ADMIN | 超级管理员，拥有全部权限 |
| ADMIN | 管理员，可管理租户与计费 |
| OPERATOR | 运营人员，可查看数据与处理工单 |
| VIEWER | 只读，仅可查看统计报表 |

```bash
# 超级管理员登录
curl -X POST "http://localhost:8000/api/v1/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123456"}'
```

### 2. 租户管理

- **租户列表**：分页查询、按名称/状态/套餐筛选
- **租户详情**：查看租户基本信息、当前套餐、用量统计
- **创建租户**：手动创建租户并分配初始套餐
- **启用 / 停用**：一键切换租户状态，停用后 API Key 立即失效
- **配额调整**：手动增减租户配额（对话次数、存储空间等）
- **服务延期**：延长租户订阅有效期
- **功能模块授权**：按需开启或关闭特定功能模块

### 3. 订阅管理

- **套餐配置**：创建、编辑订阅套餐（名称、价格、功能模块、配额限制）
- **订阅列表**：查看所有租户的订阅状态与到期时间
- **套餐变更记录**：追踪租户套餐升降级历史

### 4. 支付与账单

- **支付订单**：查看全平台支付记录，支持按租户、时间、状态筛选
- **账单管理**：月度账单生成与查看
- **退款处理**：发起退款并记录退款原因
- **发票管理**：审核租户发票申请，管理发票开具状态
- **财务报表**：收入趋势、套餐分布、月度对比分析

### 5. 平台统计

- **平台概览**：总租户数、活跃租户、今日对话量、月度收入
- **用量趋势**：按天/周/月展示对话量、API 调用量趋势图
- **收入分析**：收入趋势、套餐收入占比、租户 ARPU 分析
- **租户增长**：新增租户趋势、留存率分析

### 6. 管理员账号管理

- **账号 CRUD**：创建、编辑、删除管理员账号
- **权限分配**：为管理员分配角色或使用权限模板
- **权限模板**：预设常用权限组合，快速批量授权

### 7. 审计日志

- **操作记录**：记录所有管理员操作（登录、租户变更、配置修改等）
- **安全事件**：异常登录、权限越权等安全事件追踪
- **日志查询**：按操作人、操作类型、时间范围筛选
- **日志导出**：支持导出审计日志用于合规审查

### 8. 平台配置

#### 系统设置

- 平台基础信息配置
- 功能开关（全局启用/禁用特定功能）
- 限流规则配置（API 请求频率限制）

#### 敏感词过滤

- 维护敏感词库（新增、删除、批量导入）
- 配置过滤策略（拦截 / 替换 / 告警）
- 查看敏感词触发记录

## 📡 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Next.js 前端 | 80 | 用户端 + 管理后台 Web UI（通过 rewrites 代理 API） |
| FastAPI 后端 | 8000 | REST API & WebSocket |
| PostgreSQL | 5432 | 主数据库 |
| Redis | 6379 | 缓存 & Celery Broker |
| Milvus | 19530 | 向量数据库 |
| MinIO | 9000/9001 | 对象存储（API / Console） |
| RabbitMQ AMQP | 5672 | 消息队列 |
| RabbitMQ 管理 | 15672 | 管理界面（guest/guest） |

## 📖 API 文档

启动服务后访问 **http://localhost:8000/docs** 查看完整的交互式 Swagger 文档。

### 主要端点概览

| 模块 | 端点前缀 | 说明 |
|------|---------|------|
| 认证 | `/api/v1/auth` | 登录、Token 刷新 |
| 租户 | `/api/v1/tenant` | 注册、订阅、配额、用量 |
| 对话 | `/api/v1/conversation` | 会话 CRUD、消息管理 |
| AI 对话 | `/api/v1/ai-chat` | 智能对话、意图分类、实体提取 |
| WebSocket | `/api/v1/ws/chat` | 实时流式对话 |
| 商品 | `/api/v1/products` | 商品 CRUD、平台同步、提示词管理 |
| 内容生成 | `/api/v1/content` | 海报/视频/文案生成、素材管理、Provider 能力查询 |
| 知识库 | `/api/v1/knowledge` | CRUD、搜索、批量导入 |
| RAG | `/api/v1/rag` | 检索、生成、索引 |
| 智能定价 | `/api/v1/pricing` | 竞品管理、定价分析、AI 建议 |
| 订单 | `/api/v1/orders` | 订单同步、分析、热销排行 |
| 分析报告 | `/api/v1/reports` | 日/周/月报告生成与管理 |
| 意图 | `/api/v1/intent` | 意图分类、实体提取 |
| 平台对接 | `/api/v1/platform` | 拼多多 OAuth、消息回复 |
| 监控 | `/api/v1/monitor` | 统计、趋势、Dashboard |
| 质量 | `/api/v1/quality` | 对话质量评估 |
| Webhook | `/api/v1/webhooks` | 创建、测试、列表 |
| 支付 | `/api/v1/payment` | 订单、回调 |
| 管理员 | `/api/v1/admin` | 租户管理、统计报表 |
| 数据分析 | `/api/v1/analytics` | 增长分析、流失分析、LTV 分析 |
| 审计 | `/api/v1/audit` | 审计日志查询 |
| 敏感词 | `/api/v1/sensitive-word` | 敏感词管理 |
| 系统初始化 | `/api/v1/setup` | 首次部署初始化 |
| 健康检查 | `/api/v1/health` | 服务健康状态 |

## 🔧 配置说明

核心环境变量（`docker-compose.yml` / `.env`）：

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://ecom_user:ecom_password@postgres:5432/ecom_chatbot

# Redis
REDIS_URL=redis://redis:6379/0

# 向量数据库
MILVUS_HOST=milvus
MILVUS_PORT=19530

# JWT
JWT_SECRET=change-this-in-production
JWT_ACCESS_TOKEN_EXPIRE_HOURS=8
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# MinIO 对象存储
MINIO_ENDPOINT=milvus-minio:9000
MINIO_EXTERNAL_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ecom-chatbot
```

### 火山引擎模型配置

系统使用火山引擎提供的 AI 模型服务，需要配置以下环境变量：

```env
# 火山引擎 API 配置
VOLCENGINE_API_KEY=your-api-key-here
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3

# LLM 大语言模型
LLM_PROVIDER=volcengine
LLM_MODEL=deepseek-v3-2-251201
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embedding 向量模型
EMBEDDING_PROVIDER=volcengine
EMBEDDING_MODEL=doubao-embedding-vision-251215
EMBEDDING_DIMENSION=2048

# 图片生成模型
IMAGE_GEN_PROVIDER=volcengine
IMAGE_GEN_MODEL=doubao-seedream-5-0-260128

# 视频生成模型
VIDEO_GEN_PROVIDER=volcengine
VIDEO_GEN_MODEL=doubao-seedance-1-5-pro-251215
```

请在 `.env.local` 文件中配置实际的 API Key。

## 🧪 测试

```bash
# 运行全部测试（后端 + 前端 E2E）
./run_all_tests.sh

# 仅后端测试
./scripts/run-tests.sh

# 冒烟测试（快速验证核心流程）
./scripts/smoke-test.sh

# 前端 E2E 测试
cd frontend && npm run test:e2e
```

测试覆盖：后端 API 单元测试 & 集成测试、性能基准测试、安全测试、前端 Playwright E2E 测试

## 📊 监控与日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时跟踪 API 日志
docker-compose logs -f api

# Celery Worker 日志
docker-compose logs -f celery-worker

# 所有服务状态
docker-compose ps
```

Flower（Celery 任务监控）默认随 `docker-compose up` 启动，可通过配置端口访问。

## 🛡️ 生产安全建议

1. **修改默认密码**：数据库密码、管理员密码（`admin123456`）、JWT Secret
2. **配置 HTTPS**：通过 Nginx 反向代理挂载 SSL 证书
3. **收紧防火墙**：只对外暴露 80/443，其余端口仅内网可访问
4. **定期数据备份**：
   ```bash
   docker-compose exec postgres pg_dump -U ecom_user ecom_chatbot > backup_$(date +%Y%m%d).sql
   ```
5. **密钥管理**：通过环境变量或 Secrets Manager 注入敏感配置，禁止提交到 Git

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 资源链接

- **交互式 API 文档**：http://localhost:8000/docs
- **设计方案**：[docs/设计方案.md](./docs/设计方案.md)
- **快速开始**：[docs/QUICKSTART.md](./docs/QUICKSTART.md)
- **部署指南**：[docs/README-DEPLOYMENT.md](./docs/README-DEPLOYMENT.md)
- **支付集成**：[docs/alipay-integration-guide.md](./docs/alipay-integration-guide.md)
- **性能优化**：[docs/performance-optimization-guide.md](./docs/performance-optimization-guide.md)
- **问题反馈**：GitHub Issues

## 🙏 致谢

[FastAPI](https://fastapi.tiangolo.com/) · [Next.js](https://nextjs.org/) · [LangChain](https://python.langchain.com/) · [Milvus](https://milvus.io/) · [Ant Design](https://ant.design/) · [SQLAlchemy](https://www.sqlalchemy.org/) · [PostgreSQL](https://www.postgresql.org/) · [Redis](https://redis.io/) · [MinIO](https://min.io/)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
