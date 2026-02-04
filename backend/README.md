# 后端服务

电商智能客服 SaaS 平台后端 API 服务

## 目录结构

```
backend/
├── api/              # API 路由
│   ├── main.py      # FastAPI 应用入口
│   ├── dependencies.py  # 依赖注入
│   └── routers/     # 路由模块
├── core/            # 核心配置
│   ├── config.py    # 配置管理
│   ├── security.py  # 安全模块
│   ├── exceptions.py  # 异常定义
│   └── permissions.py  # 权限管理
├── models/          # 数据库模型
├── schemas/         # Pydantic 验证模型
├── services/        # 业务逻辑服务
├── db/             # 数据库连接
├── migrations/      # 数据库迁移
├── requirements.txt # Python 依赖
├── Dockerfile      # Docker 镜像
└── .env.example    # 环境变量示例
```

## 快速开始

### 本地开发

```bash
# 1. 创建虚拟环境
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 启动服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 部署

在项目根目录运行：

```bash
docker-compose up -d
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 测试

```bash
pytest
pytest --cov=. --cov-report=html
```
