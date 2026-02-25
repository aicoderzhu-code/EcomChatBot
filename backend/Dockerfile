# 多阶段构建 Dockerfile

# 阶段1: 基础镜像
FROM python:3.11.14-slim as base

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阶段2: 生产镜像
FROM python:3.11.14-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 从基础镜像复制已安装的依赖
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 复制并设置启动脚本权限
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 创建非 root 用户（但不立即切换）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# 暴露端口
EXPOSE 8000

# 使用入口脚本
ENTRYPOINT ["/docker-entrypoint.sh"]

# 默认启动命令（使用多 workers 避免单进程阻塞）
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "30"]
