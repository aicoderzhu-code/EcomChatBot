# Jenkins CI/CD Docker 测试环境

本目录包含用于 Jenkins CI/CD 的 Docker 配置文件，实现完全容器化的自动化测试。

## 文件说明

- `Dockerfile` - 测试运行器的 Docker 镜像定义
- `docker-compose.yml` - Docker Compose 编排配置
- `README.md` - 本文档

## 环境要求

### Jenkins 服务器要求

- ✅ Docker Engine 20.10+
- ✅ Docker Compose 1.29+ (可选，用于本地测试)
- ❌ 不需要 Python 环境
- ❌ 不需要 Conda
- ❌ 不需要 virtualenv

### 优势

1. **环境一致性**: 所有测试在完全相同的 Docker 容器中运行
2. **零依赖**: Jenkins 服务器只需要 Docker
3. **易于扩展**: 可以轻松添加更多测试依赖
4. **隔离性好**: 每次测试在独立容器中运行，互不干扰
5. **可复现**: 本地和 CI 环境完全一致

## 使用方法

### 方式一: 使用 Jenkins Pipeline (推荐)

Jenkins Pipeline 会自动：
1. 构建测试 Docker 镜像
2. 在容器中运行测试
3. 收集测试报告
4. 清理旧镜像

无需手动操作，只需触发构建即可。

### 方式二: 本地使用 Docker Compose

```bash
# 1. 进入项目根目录
cd /path/to/ecom-chat-bot

# 2. 构建并运行测试
docker-compose -f .jenkins/docker-compose.yml up --build

# 3. 仅构建镜像
docker-compose -f .jenkins/docker-compose.yml build

# 4. 运行特定测试
docker-compose -f .jenkins/docker-compose.yml run --rm test-runner \
  pytest api/ --html=reports/html/report.html

# 5. 运行完整测试套件
docker-compose -f .jenkins/docker-compose.yml run --rm test-runner \
  pytest --cov=. --cov-report=html:reports/coverage

# 6. 清理
docker-compose -f .jenkins/docker-compose.yml down
```

### 方式三: 直接使用 Docker 命令

```bash
# 1. 构建测试镜像
docker build -t ecom-chat-bot-test:latest -f .jenkins/Dockerfile .

# 2. 运行快速测试
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace/backend/tests \
  -e TEST_BASE_URL=http://115.190.75.88:8000 \
  ecom-chat-bot-test:latest \
  pytest -m "not slow" --html=reports/html/report.html

# 3. 运行完整测试
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace/backend/tests \
  -e TEST_BASE_URL=http://115.190.75.88:8000 \
  ecom-chat-bot-test:latest \
  pytest --cov=. --cov-report=html:reports/coverage

# 4. 进入容器调试
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /workspace/backend/tests \
  ecom-chat-bot-test:latest \
  /bin/bash
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| TEST_BASE_URL | http://115.190.75.88:8000 | 测试服务器地址 |
| TEST_API_PREFIX | /api/v1 | API 路径前缀 |
| TEST_REQUEST_TIMEOUT | 30 | 请求超时时间（秒） |
| TEST_LLM_REQUEST_TIMEOUT | 60 | LLM 请求超时时间（秒） |
| TEST_CLEANUP_AFTER_TEST | true | 测试后是否清理数据 |
| TEST_SKIP_PERFORMANCE | true | 是否跳过性能测试 |
| TEST_SKIP_SECURITY | true | 是否跳过安全测试 |
| TEST_LOG_LEVEL | INFO | 日志级别 |
| TEST_TENANT_PREFIX | ci_test_ | 测试租户前缀 |
| TEST_MAX_CONCURRENT | 10 | 最大并发数 |

## 镜像构建说明

### 基础镜像
- `python:3.11-slim` - 轻量级 Python 3.11 镜像

### 安装的依赖
- 系统依赖: curl, git, gcc
- Python 依赖: 从 `backend/tests/requirements-test.txt` 安装

### 构建参数
- 使用国内镜像源 (清华大学 PyPI 镜像) 加速
- 不缓存 pip 下载，减小镜像体积

### 镜像大小
- 约 500-800 MB（包含所有测试依赖）

## Jenkins Pipeline 配置

### 构建参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| TEST_LEVEL | Choice | quick | 测试级别 |
| SKIP_SLOW_TESTS | Boolean | true | 跳过慢速测试 |
| RUN_PERFORMANCE_TESTS | Boolean | false | 运行性能测试 |
| RUN_SECURITY_TESTS | Boolean | false | 运行安全测试 |
| CLEANUP_TEST_DATA | Boolean | true | 清理测试数据 |
| REBUILD_IMAGE | Boolean | false | 强制重建镜像 |

### 测试级别说明

- **quick**: 快速测试，跳过慢速、性能和安全测试
- **full**: 完整测试，包含代码覆盖率
- **api**: 仅 API 测试
- **integration**: 仅集成测试
- **performance**: 仅性能测试
- **security**: 仅安全测试

### Pipeline 流程

```
1. 准备环境
   ├── 检出代码
   └── 显示构建信息

2. 检查环境
   ├── 检查 Docker
   ├── 检查 Docker Compose
   └── 检查测试服务器

3. 构建测试镜像
   ├── 构建 Docker 镜像
   └── 标记版本

4. 配置测试环境
   └── 创建报告目录

5. 运行测试
   ├── 在容器中运行 pytest
   └── 生成测试报告

6. 收集测试报告
   ├── 发布 JUnit 报告
   ├── 发布 HTML 报告
   └── 发布覆盖率报告

7. 分析测试结果
   ├── 计算测试指标
   └── 判断构建状态

8. 清理
   ├── 清理 Python 缓存
   └── 清理旧 Docker 镜像
```

## 测试报告

### 报告位置
- JUnit XML: `backend/tests/reports/junit.xml`
- HTML 报告: `backend/tests/reports/html/report.html`
- 覆盖率报告: `backend/tests/reports/coverage/index.html`

### 访问报告
- Jenkins 中可以直接查看 HTML 报告
- 报告会被归档，可以下载查看

## 故障排查

### 问题 1: Docker 镜像构建失败

```bash
# 检查 Docker 服务
docker info

# 清理 Docker 缓存
docker system prune -a

# 强制重新构建
docker build --no-cache -t ecom-chat-bot-test:latest -f .jenkins/Dockerfile .
```

### 问题 2: 测试服务器不可访问

```bash
# 从容器内测试连接
docker run --rm ecom-chat-bot-test:latest \
  curl -v http://115.190.75.88:8000/health
```

### 问题 3: 依赖安装失败

```bash
# 检查 requirements-test.txt
cat backend/tests/requirements-test.txt

# 手动测试安装
docker run --rm -it ecom-chat-bot-test:latest \
  pip install -r /workspace/backend/tests/requirements-test.txt
```

### 问题 4: 权限问题

```bash
# 检查文件权限
ls -la backend/tests/reports/

# 修复权限（在宿主机上）
chmod -R 755 backend/tests/reports/
```

### 问题 5: 磁盘空间不足

```bash
# 检查 Docker 占用空间
docker system df

# 清理未使用的镜像
docker image prune -a

# 清理所有未使用的资源
docker system prune -a --volumes
```

## 性能优化

### 1. 使用镜像缓存

Jenkins Pipeline 默认会缓存镜像，只有以下情况会重建：
- Dockerfile 或 requirements-test.txt 变更
- 手动设置 `REBUILD_IMAGE = true`

### 2. 使用国内镜像源

Dockerfile 中已配置清华大学 PyPI 镜像：
```dockerfile
RUN pip install -r requirements-test.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 定期清理旧镜像

Jenkins Pipeline 会自动保留最近 3 个测试镜像，删除更旧的版本。

### 4. 并行构建（高级）

如果有多个项目，可以配置 Jenkins 并行构建不同的测试镜像。

## 安全建议

1. **不要在镜像中包含敏感信息**
   - 不要将 API Key、密码等写入 Dockerfile
   - 使用环境变量传递敏感信息

2. **定期更新基础镜像**
   ```bash
   # 拉取最新基础镜像
   docker pull python:3.11-slim
   
   # 重新构建
   docker build --no-cache -t ecom-chat-bot-test:latest -f .jenkins/Dockerfile .
   ```

3. **使用官方镜像**
   - 只使用官方或可信的基础镜像
   - 定期扫描镜像漏洞

4. **最小化镜像体积**
   - 使用 slim 版本基础镜像
   - 清理不必要的文件和缓存

## 本地开发测试

### 快速测试

```bash
# 使用 Docker Compose
docker-compose -f .jenkins/docker-compose.yml up
```

### 调试模式

```bash
# 进入容器
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /workspace/backend/tests \
  ecom-chat-bot-test:latest \
  /bin/bash

# 在容器内手动运行测试
pytest api/test_auth.py -v
```

### 监听文件变化

可以使用 Docker volume 挂载代码目录，实现代码变更实时生效。

## 常见问题

**Q: 为什么不使用 Conda？**  
A: Conda 会增加镜像体积（约 500MB+），而 pip + venv 足够满足需求。

**Q: 如何加速镜像构建？**  
A: 使用国内镜像源、利用 Docker 缓存、减少不必要的层。

**Q: 如何在 Windows 上使用？**  
A: 需要安装 Docker Desktop for Windows，路径需要调整。

**Q: 测试报告在哪里？**  
A: `backend/tests/reports/` 目录，Jenkins 会自动发布。

**Q: 如何添加新的测试依赖？**  
A: 在 `backend/tests/requirements-test.txt` 中添加，重新构建镜像。

## 联系支持

如遇问题，请：
- 查看 Jenkins 构建日志
- 检查 Docker 日志: `docker logs <container-id>`
- 在项目仓库提交 Issue

---

最后更新: 2026-02-10
