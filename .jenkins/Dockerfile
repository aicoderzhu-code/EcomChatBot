# Jenkins Test Docker Image
# 用于在 Docker 容器中运行自动化测试

FROM python:3.11-slim

LABEL maintainer="ecom-chat-bot-team"
LABEL description="Test runner for ecom-chat-bot project"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=1000

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /workspace

# 复制测试依赖文件
COPY backend/tests/requirements-test.txt /tmp/requirements-test.txt

# 安装测试依赖
RUN pip install --no-cache-dir -r /tmp/requirements-test.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    rm /tmp/requirements-test.txt

# 创建报告目录
RUN mkdir -p /workspace/backend/tests/reports

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python --version || exit 1

# 默认命令
CMD ["/bin/bash"]
