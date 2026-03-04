# 部署指南

本项目支持开发环境和生产环境的独立部署配置。通过环境变量驱动，同一套代码可以在不同环境中运行。

## 快速开始

### 开发环境部署

1. **配置本机IP地址**

   编辑 `.env.development` 文件，将 `HOST_IP` 修改为你的本机IP地址：

   ```bash
   # 查看本机IP
   ifconfig | grep "inet " | grep -v 127.0.0.1

   # 编辑配置文件
   vim .env.development
   ```

   修改为：
   ```bash
   HOST_IP=192.168.1.100  # 替换为你的实际IP
   ```

2. **运行部署脚本**

   ```bash
   ./deploy-dev.sh
   ```

3. **访问系统**

   ```
   http://192.168.1.100
   ```

### 生产环境部署

1. **确保SSL证书已放置**

   将SSL证书文件放置在 `./ssl/` 目录：
   - `cert.pem` - SSL证书
   - `key.pem` - 私钥

2. **运行部署脚本**

   ```bash
   ./deploy-prod.sh
   ```

3. **访问系统**

   ```
   https://ecomchat.cn
   ```

## 手动部署

如果不使用部署脚本，可以手动执行以下命令：

### 开发环境
```bash
export DEPLOY_ENV=development
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 生产环境
```bash
export DEPLOY_ENV=production
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 环境切换

停止当前环境：
```bash
docker compose down
```

启动目标环境：
```bash
# 开发环境
./deploy-dev.sh

# 或生产环境
./deploy-prod.sh
```

## 配置文件说明

### 环境配置文件结构

```
project/
├── .env.development          # 开发环境共享配置
├── backend/
│   ├── .env.development      # 后端开发配置
│   └── .env.production       # 后端生产配置
├── frontend/
│   ├── .env.development      # 前端开发配置
│   └── .env.production       # 前端生产配置
├── nginx/
│   ├── conf.d/
│   │   ├── development.conf  # 开发环境Nginx配置
│   │   └── ecomchat.conf     # 生产环境Nginx配置
├── docker-compose.yml        # 基础配置
├── docker-compose.dev.yml    # 开发环境覆盖配置
└── docker-compose.prod.yml   # 生产环境覆盖配置
```

### 关键差异

| 配置项 | 开发环境 | 生产环境 |
|--------|---------|---------|
| 协议 | HTTP | HTTPS |
| 域名/IP | 本机IP (如 192.168.1.100) | ecomchat.cn |
| WebSocket | ws:// | wss:// |
| CORS | 允许所有来源 | 仅允许域名 |
| DEBUG | true | false |
| SSL证书 | 不需要 | 必需 |
| 日志级别 | DEBUG | INFO |

## 常用命令

### 查看服务状态
```bash
docker compose ps
```

### 查看日志
```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f nginx
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart api
```

### 停止服务
```bash
docker compose down
```

### 清理并重新构建
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 故障排查

### 问题1：Nginx启动失败（SSL证书错误）

**现象**：
```
nginx: [emerg] cannot load certificate "/etc/nginx/ssl/cert.pem"
```

**解决方案**：
- 开发环境：使用 `./deploy-dev.sh`，不需要SSL证书
- 生产环境：确保 `./ssl/` 目录下有 `cert.pem` 和 `key.pem` 文件

### 问题2：CORS错误

**现象**：
```
Access to XMLHttpRequest has been blocked by CORS policy
```

**解决方案**：
- 检查 `backend/.env.development` 中的 `CORS_ORIGINS` 配置
- 确保包含前端访问地址（如 `http://192.168.1.100`）
- 重启API服务：`docker compose restart api`

### 问题3：WebSocket连接失败

**现象**：
```
WebSocket connection to 'ws://...' failed
```

**解决方案**：
- 检查 `frontend/.env.development` 中的 `NEXT_PUBLIC_WS_BASE_URL`
- 开发环境使用 `ws://`，生产环境使用 `wss://`
- 确保IP地址配置正确
- 检查Nginx配置：`docker compose logs nginx`

### 问题4：环境变量未生效

**现象**：
配置修改后，系统行为未改变

**解决方案**：
```bash
# 停止所有容器
docker compose down

# 清理镜像缓存
docker compose build --no-cache

# 重新启动
./deploy-dev.sh  # 或 ./deploy-prod.sh
```

### 问题5：无法访问（连接超时）

**现象**：
浏览器显示"无法访问此网站"

**解决方案**：
- 检查防火墙是否允许80/443端口
- 确认Docker容器正在运行：`docker compose ps`
- 检查Nginx日志：`docker compose logs nginx`
- 验证IP地址配置正确
- 确保局域网内其他设备可以访问该IP

### 问题6：前端环境变量未更新

**现象**：
修改了 `.env.development` 但前端仍使用旧配置

**原因**：
Next.js 的 `NEXT_PUBLIC_*` 变量在构建时打包到代码中

**解决方案**：
```bash
# 必须重新构建前端镜像
docker compose build --no-cache frontend
docker compose up -d frontend
```

## 注意事项

1. **IP地址配置**
   - 开发环境需要手动配置 `HOST_IP`
   - 使用 `ifconfig` 或 `ip addr` 查看本机IP
   - 确保局域网内其他设备可访问该IP

2. **SSL证书**
   - 生产环境必须提供有效的SSL证书
   - 证书文件路径：`./ssl/cert.pem` 和 `./ssl/key.pem`
   - 开发环境不需要SSL证书

3. **数据库数据**
   - 开发和生产环境共享同一个数据库容器
   - 如需隔离，可创建不同的数据库实例
   - 建议生产环境使用外部数据库服务

4. **端口冲突**
   - 确保80和443端口未被占用
   - 开发环境可修改端口映射：编辑 `docker-compose.dev.yml`

5. **环境变量文件**
   - `.env.*` 文件包含敏感信息，不应提交到Git
   - 已在 `.gitignore` 中排除
   - 团队成员需要自行创建配置文件

6. **Docker镜像缓存**
   - 切换环境后建议重新构建：`docker compose build --no-cache`
   - 避免使用旧环境的缓存配置

7. **前端环境变量**
   - `NEXT_PUBLIC_*` 变量在构建时打包
   - 修改后必须重新构建前端镜像
   - 运行时无法修改这些变量

## 技术架构

### Docker Compose多文件支持

使用 `-f` 参数组合多个配置文件：
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

配置合并规则：
- 后面的文件覆盖前面的文件
- 数组类型（如 volumes）会合并
- 对象类型（如 environment）会覆盖

### 环境变量优先级

从高到低：
1. `docker-compose.yml` 中的 `environment` 字段
2. `env_file` 指定的文件
3. Shell环境变量
4. `.env` 文件（Docker Compose默认加载）

### Nginx配置动态加载

通过挂载不同的配置文件实现：
```yaml
volumes:
  - ./nginx/conf.d/development.conf:/etc/nginx/conf.d/default.conf:ro
```

## 安全考虑

### 开发环境
- 允许所有来源的CORS请求
- 关闭HTTPS（简化开发）
- 允许IP直接访问
- 开启DEBUG模式

### 生产环境
- 严格限制CORS来源
- 强制HTTPS
- 拒绝非域名访问
- 关闭DEBUG模式
- 启用安全头部（HSTS、X-Frame-Options等）

## 更多帮助

如遇到其他问题，请查看：
- 项目文档：`docs/` 目录
- 配置说明：`CONFIG.md`
- 部署检查清单：`DEPLOYMENT_CHECKLIST.md`
