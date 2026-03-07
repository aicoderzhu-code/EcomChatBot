# 数据库初始化说明

## 概述

本项目使用 `backend/init_db.py` 进行数据库初始化，**不需要运行数据库迁移文件**。

## 初始化方式

### 自动初始化（Docker 部署）

使用 Docker Compose 部署时，`db-init` 容器会自动运行 `init_db.py`：

```bash
docker compose up -d
```

`db-init` 容器会：
1. 等待 PostgreSQL 数据库就绪
2. 运行 `python init_db.py`
3. 完成后自动退出

### 手动初始化（本地开发）

```bash
cd backend
python init_db.py
```

## 初始化内容

`init_db.py` 会自动完成以下操作：

### 1. 创建所有数据库表（47 张表）

使用 SQLAlchemy 的 `Base.metadata.create_all()` 自动创建所有表：

- 租户相关：tenants, subscriptions, bills
- 用户相关：users, conversations, messages
- 知识库：knowledge_base, knowledge_settings, knowledge_usage_logs
- 商品管理：products, product_prompts, platform_sync_tasks, product_sync_schedules
- 内容生成：generation_tasks, generated_assets, content_templates, platform_media_specs
- 定价分析：competitor_products, pricing_analyses
- 订单分析：orders, analysis_reports
- 客户触达：customer_segments, customer_segment_members, outreach_campaigns, outreach_rules, outreach_tasks
- 跟进推荐：follow_up_plans, recommendation_rules, recommendation_logs
- 支付相关：payment_orders, payment_transactions, payment_channel_configs, invoices, invoice_titles
- 平台管理：platform_admins, admin_operation_logs, permission_templates, platform_configs, platform_apps
- 审计日志：audit_logs
- 通知相关：in_app_notifications, notification_preferences, webhook_configs, webhook_logs, webhook_events
- 其他：after_sale_records, sensitive_words

### 2. 创建默认超级管理员

- **用户名**：`admin`
- **密码**：`admin123456`
- **角色**：超级管理员
- **邮箱**：`admin@example.com`

⚠️ **生产环境请立即修改默认密码！**

### 3. 预置系统内容模板

自动创建 13 个系统内容模板：

**海报模板（8 个）**：
- 白底商品主图
- 场景化商品主图
- 商品详情长图
- 促销活动海报
- 节日主题海报
- 直播封面
- 店铺 Banner
- 商品对比图

**视频模板（5 个）**：
- 商品主图视频
- 商品展示短视频
- 商品详情视频
- 开箱视频
- 使用教程视频

### 4. 预置平台媒体规范

为 5 个电商平台预置媒体规范（共 20 条）：
- 淘宝（4 条）
- 拼多多（4 条）
- 抖音（4 条）
- 京东（4 条）
- 快手（4 条）

每个平台包含：主图、详情图、主图视频、短视频的尺寸和格式要求。

## 幂等性

`init_db.py` 可以安全地重复运行：

- 如果表已存在，不会重复创建
- 如果管理员已存在，跳过创建
- 如果系统模板已存在，跳过创建
- 如果平台规范已存在，跳过创建

## 完全重新初始化

如果需要完全清空数据库并重新初始化：

```bash
# Docker 部署
docker compose down -v  # 删除所有容器和数据卷
docker compose up -d    # 重新启动，自动初始化

# 本地开发
# 1. 删除数据库
docker compose exec postgres psql -U ecom_user -d postgres -c "DROP DATABASE IF EXISTS ecom_chatbot;"
docker compose exec postgres psql -U ecom_user -d postgres -c "CREATE DATABASE ecom_chatbot;"

# 2. 重新初始化
cd backend
python init_db.py
```

## 为什么不使用数据库迁移？

本项目选择使用 `init_db.py` 而不是 Alembic 迁移的原因：

1. **简化部署**：不需要管理迁移文件，部署时直接运行 `init_db.py` 即可
2. **完整性保证**：每次部署都创建完整的数据库结构，避免迁移文件不一致
3. **开发灵活性**：开发时可以随时删除数据库重新初始化，无需回滚迁移
4. **适合 SaaS**：多租户架构下，数据隔离通过 `tenant_id` 实现，不需要频繁修改表结构

## 数据库表列表

完整的 47 张表：

```
admin_operation_logs
after_sale_records
analysis_reports
audit_logs
bills
competitor_products
content_templates
conversations
customer_segment_members
customer_segments
follow_up_plans
generated_assets
generation_tasks
in_app_notifications
invoice_titles
invoices
knowledge_base
knowledge_settings
knowledge_usage_logs
messages
notification_preferences
orders
outreach_campaigns
outreach_rules
outreach_tasks
payment_channel_configs
payment_orders
payment_transactions
permission_templates
platform_admins
platform_apps
platform_configs
platform_media_specs
platform_sync_tasks
pricing_analyses
product_prompts
product_sync_schedules
products
recommendation_logs
recommendation_rules
sensitive_words
subscriptions
tenants
users
webhook_configs
webhook_events
webhook_logs
```

## 验证初始化

检查数据库表是否创建成功：

```bash
# 查看所有表
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "\dt"

# 查看表数量（应该是 47）
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# 验证管理员账号
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "SELECT username, email, role FROM platform_admins;"

# 验证系统模板
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "SELECT COUNT(*) FROM content_templates WHERE is_system = 1;"

# 验证平台规范
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "SELECT COUNT(*) FROM platform_media_specs;"
```

## 故障排查

### 问题：数据库连接失败

```bash
# 检查 PostgreSQL 容器状态
docker compose ps postgres

# 查看 PostgreSQL 日志
docker compose logs postgres

# 检查数据库连接
docker compose exec postgres psql -U ecom_user -d ecom_chatbot -c "SELECT 1;"
```

### 问题：初始化失败

```bash
# 查看 db-init 容器日志
docker compose logs db-init

# 手动运行初始化
docker compose exec api python init_db.py
```

### 问题：表已存在错误

这是正常的，`init_db.py` 会跳过已存在的表。如果需要重新创建，请参考"完全重新初始化"部分。

## 相关文件

- `backend/init_db.py` - 数据库初始化脚本
- `backend/models/__init__.py` - 所有模型导入
- `backend/models/base.py` - Base 模型定义
- `docker-compose.yml` - db-init 服务配置
