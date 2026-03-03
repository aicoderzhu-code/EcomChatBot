# 环境变量配置指南

本文档说明项目的环境变量配置结构和使用方法。

## 配置文件结构

```
ecom-chat-bot/
├── .env.local                    # 共享配置（TOS等，gitignore）
├── .env.example                  # 共享配置示例
├── backend/
│   ├── .env                      # 后端主配置（gitignore）
│   ├── .env.example              # 后端配置示例
│   ├── .env.development          # 开发环境默认配置
│   └── .env.production.template  # 生产环境配置模板
├── frontend/
│   ├── .env.local                # 前端本地配置（gitignore）
│   ├── .env.example              # 前端配置示例
│   ├── .env.development          # 前端开发默认配置
│   └── .env.production           # 前端生产配置
└── docker-compose.yml            # Docker配置（引用上述文件）
```

## 配置分层说明

### 1. 共享配置（根目录）

**文件**: `.env.local`（不提交到Git）

**用途**: 存储多个服务共享的配置，主要是火山引擎TOS对象存储凭证

**内容**:
- TOS_ACCESS_KEY
- TOS_SECRET_KEY
- TOS_ENDPOINT
- TOS_REGION
- TOS_BUCKET

### 2. 后端配置（backend/）

**主配置文件**: `backend/.env`（不提交到Git）
- 优先级最高
- 包含所有后端服务需要的环境变量
- 本地开发和生产部署都使用此文件

**开发默认配置**: `backend/.env.development`（可提交）
- 包含开发环境的默认值
- 可作为参考，但实际配置以 `.env` 为准

**生产配置模板**: `backend/.env.production.template`（可提交）
- 生产环境配置模板
- 部署时复制为 `.env` 并填入实际值

**示例文件**: `backend/.env.example`（可提交）
- 使用占位符，不包含实际凭证
- 新成员参考此文件创建自己的 `.env`

### 3. 前端配置（frontend/）

**本地开发**: `frontend/.env.local`（不提交到Git）
- 本地开发时的配置
- 覆盖 `.env.development` 的默认值

**开发默认**: `frontend/.env.development`（可提交）
- 开发环境默认配置
- API地址指向本地后端服务

**生产配置**: `frontend/.env.production`（可提交）
- 生产环境配置
- API请求通过Next.js rewrites代理

## 快速开始

### 首次设置（新成员）

1. **创建根目录共享配置**
   ```bash
   cp .env.example .env.local
   # 编辑 .env.local，填入实际的TOS凭证
   ```

2. **创建后端配置**
   ```bash
   cp backend/.env.example backend/.env
   # 编辑 backend/.env，填入实际的API Key、数据库凭证等
   ```

3. **创建前端配置（可选）**
   ```bash
   # 如果需要自定义API地址
   cp frontend/.env.example frontend/.env.local
   ```

### 本地开发

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f api
```

### 生产部署

1. **准备配置文件**
   ```bash
   # 创建共享配置
   cp .env.example .env.local
   # 填入生产环境的TOS凭证

   # 创建后端配置
   cp backend/.env.production.template backend/.env
   # 填入生产环境的所有凭证和配置
   ```

2. **部署服务**
   ```bash
   docker compose build
   docker compose up -d
   ```

## 配置读取优先级

### 后端（Pydantic Settings）
1. 环境变量（最高优先级）
2. `.env` 文件
3. 代码中的默认值

### 前端（Next.js）
1. `.env.local`（最高优先级，gitignore）
2. `.env.development` 或 `.env.production`（根据NODE_ENV）
3. `.env`（最低优先级）

### Docker Compose
1. `environment` 部分的直接定义（最高优先级）
2. `env_file` 指定的文件（按顺序加载）
3. 宿主机环境变量

## 重要配置项说明

### 必填配置

以下配置项必须填写实际值，否则服务无法正常运行：

**后端**:
- `JWT_SECRET`: JWT密钥（生产环境必须使用强密钥）
- `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`: LLM API密钥
- `MILVUS_URI` 和 `MILVUS_TOKEN`: 向量数据库凭证
- `TOS_ACCESS_KEY` 和 `TOS_SECRET_KEY`: 对象存储凭证

**前端**:
- `NEXT_PUBLIC_API_BASE_URL`: API基础地址

### 可选配置

以下配置项可以留空或使用默认值：

- `ANTHROPIC_API_KEY`: 如果不使用Claude模型可以留空
- `ALIPAY_*`: 如果不使用支付功能可以留空
- `SMTP_*`: 如果不使用邮件服务可以留空
- `SENTRY_DSN`: 如果不使用Sentry监控可以留空

## 安全注意事项

1. **永远不要提交包含实际凭证的文件**
   - `.env`
   - `.env.local`
   - `backend/.env`
   - `frontend/.env.local`

2. **示例文件必须使用占位符**
   - `.env.example`
   - `backend/.env.example`
   - `frontend/.env.example`

3. **生产环境密钥管理**
   - JWT_SECRET: 使用 `openssl rand -hex 32` 生成强密钥
   - 数据库密码: 使用强密码，不要使用默认值
   - API Key: 定期轮换，限制权限范围

4. **检查Git状态**
   ```bash
   # 确认敏感文件被忽略
   git status --ignored

   # 确认示例文件不含实际凭证
   grep -r "AKLTMmQx" .env.example backend/.env.example frontend/.env.example
   ```

## 常见问题

### Q: 为什么有这么多配置文件？

A: 不同的配置文件服务于不同的目的：
- `.example` 文件：供新成员参考
- `.development` 文件：提供开发环境默认值
- `.template` 文件：提供生产环境配置模板
- `.env` 和 `.env.local`：实际使用的配置（不提交）

### Q: 本地开发时应该修改哪个文件？

A: 修改 `backend/.env` 和 `frontend/.env.local`（如果需要）

### Q: Docker Compose 从哪里读取配置？

A: Docker Compose 通过 `env_file` 指令读取 `.env.local` 和 `backend/.env`，然后用 `environment` 部分的配置覆盖特定的值（如数据库地址）

### Q: 如何验证配置是否正确？

A:
```bash
# 检查后端读取的配置
docker compose exec api python -c "from core.config import settings; print(settings.tos_access_key[:10])"

# 检查环境变量注入
docker compose exec api env | grep TOS
```

### Q: 生产环境部署时需要注意什么？

A:
1. 使用 `backend/.env.production.template` 作为模板创建 `backend/.env`
2. 填入所有实际的凭证和配置
3. 确保 `JWT_SECRET` 使用强密钥
4. 确保数据库密码使用强密码
5. 设置 `DEBUG=false` 和 `ENVIRONMENT=production`

## 配置变更历史

### 2024-03-03: 环境变量优化
- 创建统一的配置文件结构
- 移除硬编码的敏感信息
- 添加开发和生产环境配置模板
- 更新 docker-compose.yml 使用 env_file
- 添加详细的配置文档

## 相关文档

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Next.js 环境变量](https://nextjs.org/docs/basic-features/environment-variables)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
