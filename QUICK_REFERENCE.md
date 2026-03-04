# 快速参考指南

## 一键部署

### 开发环境
```bash
# 1. 修改IP地址
vim .env.development  # 修改 HOST_IP=你的本机IP

# 2. 部署
./deploy-dev.sh

# 3. 访问
# http://你的本机IP
```

### 生产环境
```bash
# 1. 确保SSL证书存在
ls ssl/cert.pem ssl/key.pem

# 2. 部署
./deploy-prod.sh

# 3. 访问
# https://ecomchat.cn
```

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f api

# 重启服务
docker compose restart
docker compose restart api

# 停止服务
docker compose down

# 环境切换
docker compose down
./deploy-dev.sh  # 或 ./deploy-prod.sh

# 验证配置
./verify-setup.sh
```

## 配置文件位置

```
开发环境配置：
  - .env.development
  - backend/.env.development
  - frontend/.env.development
  - nginx/conf.d/development.conf

生产环境配置：
  - backend/.env.production
  - frontend/.env.production
  - nginx/conf.d/ecomchat.conf
```

## 关键差异

| 项目 | 开发环境 | 生产环境 |
|------|---------|---------|
| 协议 | HTTP | HTTPS |
| 地址 | 192.168.1.100 | ecomchat.cn |
| WebSocket | ws:// | wss:// |
| DEBUG | true | false |
| SSL | 不需要 | 必需 |

## 故障排查

### CORS错误
```bash
# 检查后端配置
cat backend/.env.development | grep CORS_ORIGINS
# 应包含: http://192.168.1.100

# 重启API
docker compose restart api
```

### WebSocket连接失败
```bash
# 检查前端配置
cat frontend/.env.development | grep WS_BASE_URL
# 应为: ws://192.168.1.100/api/v1/ws

# 重新构建前端
docker compose build --no-cache frontend
docker compose up -d frontend
```

### 环境变量未生效
```bash
# 完全重建
docker compose down
docker compose build --no-cache
./deploy-dev.sh  # 或 ./deploy-prod.sh
```

## 更多帮助

详细文档：`DEPLOYMENT.md`
实施总结：`IMPLEMENTATION_SUMMARY.md`
