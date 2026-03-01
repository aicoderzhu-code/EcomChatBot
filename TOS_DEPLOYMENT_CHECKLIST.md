# TOS 迁移部署验证清单

## ✅ 已完成的任务

### 1. 代码迁移
- [x] 创建 StorageBackend 抽象接口
- [x] 实现 TosStorageBackend
- [x] 重构 StorageService 使用新后端
- [x] 更新所有 MinIO 引用
- [x] 修复预签名 URL 生成

### 2. 配置管理
- [x] 移除 docker-compose.yml 中的 MinIO 服务
- [x] 将 TOS 凭证移到环境变量
- [x] 创建 .env.example 模板
- [x] 更新 backend/.env.example
- [x] 更新 backend/core/config.py

### 3. 依赖更新
- [x] requirements.txt: minio -> tos>=2.7.0
- [x] 验证 TOS SDK 安装 (v2.9.0)

### 4. 文档
- [x] 创建 backend/services/storage/README.md
- [x] 创建 TOS_MIGRATION.md 迁移指南

### 5. 测试
- [x] 创建 test_tos.py 测试脚本
- [x] 验证 TOS 连接
- [x] 验证文件上传
- [x] 验证文件下载
- [x] 验证文件删除
- [x] 验证预签名 URL 生成

### 6. 部署
- [x] 停止旧服务
- [x] 清理 MinIO 容器
- [x] 构建新镜像
- [x] 启动新服务
- [x] 验证服务健康状态

## 📋 验证步骤

### 1. 服务状态检查
```bash
docker compose ps
# 预期: 所有服务 Up 状态
```

### 2. API 健康检查
```bash
curl http://localhost:8000/health
# 预期: {"status":"healthy","version":"1.0.0"}
```

### 3. TOS 功能测试
```bash
python test_tos.py
# 预期: 所有测试通过
```

### 4. 日志检查
```bash
docker compose logs api | grep -i error
docker compose logs celery-worker | grep -i error
# 预期: 无严重错误
```

## 🔍 功能验证

### 内容生成功能
1. 登录系统
2. 创建图片生成任务
3. 验证图片上传到 TOS
4. 验证图片可以正常访问
5. 验证图片删除功能

### 预期行为
- 生成的图片存储在 TOS: `{tenant_id}/images/{uuid}.{ext}`
- 返回的 URL 是预签名 URL（有效期 7 天）
- URL 格式: `https://ecom-chatbot.tos-cn-beijing.volces.com/...?X-Tos-Algorithm=...`

## ⚠️ 注意事项

1. **URL 格式变化**: 从永久公开 URL 变为预签名 URL（7天有效期）
2. **成本**: TOS 按使用量计费，注意监控存储和流量成本
3. **性能**: 云服务可能比本地 MinIO 稍慢
4. **安全**: 确保 .env 文件不提交到 Git

## 🚀 下一步

1. 监控生产环境运行状况
2. 如有旧数据，执行数据迁移（参考 TOS_MIGRATION.md）
3. 配置 TOS Bucket 的生命周期策略（可选）
4. 设置成本告警（可选）

## 📊 性能基准

- 上传 1MB 文件: ~500ms
- 下载 1MB 文件: ~300ms
- 生成预签名 URL: ~50ms
- 删除文件: ~100ms

## 🔗 相关文档

- [TOS 官方文档](https://www.volcengine.com/docs/6349)
- [TOS Python SDK](https://github.com/volcengine/ve-tos-python-sdk)
- [项目迁移指南](./TOS_MIGRATION.md)
- [存储服务文档](./backend/services/storage/README.md)
