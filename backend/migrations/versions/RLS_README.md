# PostgreSQL Row Level Security (RLS) 使用说明

## 概述

Row Level Security (RLS) 是 PostgreSQL 提供的数据库级别的访问控制机制，可以在数据库层面强制实现多租户数据隔离，即使应用层有漏洞也能防止数据泄露。

## 已启用 RLS 的表

以下表已启用行级安全策略：

| 表名 | 说明 | 过滤字段 |
|------|------|----------|
| `conversations` | 对话 | tenant_id |
| `messages` | 消息 | tenant_id |
| `knowledge_bases` | 知识库 | tenant_id |
| `webhook_configs` | Webhook配置 | tenant_id |
| `webhook_logs` | Webhook日志 | 通过webhook_configs关联 |
| `usage_records` | 用量记录 | tenant_id |
| `bills` | 账单 | tenant_id |
| `payment_orders` | 支付订单 | tenant_id |
| `subscriptions` | 订阅 | tenant_id |

## 工作原理

### 1. Session 变量

应用层通过设置 PostgreSQL session 变量来传递上下文信息：

```sql
-- 设置当前租户ID
SET LOCAL app.current_tenant_id = 'xxx-xxx-xxx';

-- 设置管理员模式
SET LOCAL app.is_admin = 'true';
```

### 2. RLS 策略

每个表都有相应的 RLS 策略，自动过滤数据：

```sql
CREATE POLICY conversations_isolation ON conversations
FOR ALL
USING (
    tenant_id = get_current_tenant_id()  -- 匹配当前租户
    OR is_system_admin()                 -- 或者是管理员
)
```

### 3. 辅助函数

- `get_current_tenant_id()`: 从 session 变量获取当前租户ID
- `is_system_admin()`: 检查是否为系统管理员模式

## 使用方法

### 方式 1: 上下文管理器（推荐）

```python
from db.rls import tenant_context, admin_context

# 租户查询
async with tenant_context(db, tenant_id):
    # 在这个上下文中的所有查询都会自动过滤 tenant_id
    conversations = await db.execute(
        select(Conversation)
    )
    # 只会返回该租户的对话

# 管理员查询
async with admin_context(db):
    # 可以访问所有租户的数据
    all_conversations = await db.execute(
        select(Conversation)
    )
```

### 方式 2: 依赖注入

```python
from api.dependencies import TenantDep, DBDep
from db.rls import apply_tenant_rls

@router.get("/conversations")
async def get_conversations(
    db: DBDep,
    tenant_id: TenantDep
):
    # 应用 RLS 策略
    await apply_tenant_rls(db, tenant_id)

    # 后续查询自动过滤
    conversations = await db.execute(
        select(Conversation)
    )
    return conversations
```

### 方式 3: 手动设置

```python
from db.rls import set_current_tenant, clear_rls_context

# 设置租户上下文
await set_current_tenant(db, tenant_id)

# 执行查询
conversations = await db.execute(
    select(Conversation)
)

# 清理上下文（重要！）
await clear_rls_context(db)
```

## 管理员访问

管理员需要访问所有租户数据时，启用管理员模式：

```python
from db.rls import set_admin_mode

# 启用管理员模式
await set_admin_mode(db, True)

# 查询所有租户的数据
all_tenants = await db.execute(
    select(Tenant)
)

# 关闭管理员模式
await set_admin_mode(db, False)
```

或使用上下文管理器：

```python
async with admin_context(db):
    # 在这里可以访问所有数据
    all_data = await db.query(...)
```

## 运行迁移

### 应用 RLS 策略

```bash
cd backend

# 使用 Alembic 运行迁移
alembic upgrade head
```

### 回滚 RLS 策略

```bash
# 回滚到上一个版本
alembic downgrade -1

# 或回滚到特定版本
alembic downgrade 001_rls
```

## 验证 RLS

### 1. 检查 RLS 状态

```python
from db.rls import get_rls_status

status = await get_rls_status(db)
print(status)
# {
#     "enabled_tables": ["conversations", "messages", ...],
#     "total_tables": 9,
#     "current_tenant_id": "xxx-xxx-xxx",
#     "is_admin": false
# }
```

### 2. 数据库级别验证

```sql
-- 查看启用 RLS 的表
SELECT tablename
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE t.schemaname = 'public'
AND c.relrowsecurity = true;

-- 查看表的 RLS 策略
SELECT * FROM pg_policies WHERE tablename = 'conversations';
```

### 3. 测试隔离性

```python
# 测试租户A只能看到自己的数据
tenant_a_id = "tenant-a-uuid"
tenant_b_id = "tenant-b-uuid"

# 租户A的上下文
async with tenant_context(db, tenant_a_id):
    result = await db.execute(select(Conversation))
    conversations = result.scalars().all()
    # 只能看到 tenant_a 的对话

# 租户B的上下文
async with tenant_context(db, tenant_b_id):
    result = await db.execute(select(Conversation))
    conversations = result.scalars().all()
    # 只能看到 tenant_b 的对话

# 管理员上下文
async with admin_context(db):
    result = await db.execute(select(Conversation))
    conversations = result.scalars().all()
    # 可以看到所有租户的对话
```

## 性能考虑

### 1. 索引优化

确保 `tenant_id` 字段有索引：

```sql
CREATE INDEX idx_conversations_tenant_id ON conversations(tenant_id);
CREATE INDEX idx_messages_tenant_id ON messages(tenant_id);
-- ...其他表
```

### 2. 查询计划

检查查询是否正确使用了索引：

```sql
EXPLAIN ANALYZE
SELECT * FROM conversations
WHERE tenant_id = get_current_tenant_id();
```

### 3. 性能影响

- RLS 策略在每次查询时自动应用
- 对于已有索引的列，性能影响很小（<5%）
- 推荐在高并发场景使用连接池

## 安全注意事项

### ✅ 安全最佳实践

1. **始终使用上下文管理器**
   ```python
   # 推荐
   async with tenant_context(db, tenant_id):
       await do_query()

   # 不推荐
   await set_current_tenant(db, tenant_id)
   await do_query()
   # 可能忘记清理上下文
   ```

2. **管理员操作要明确**
   ```python
   # 好的做法
   async with admin_context(db):
       # 明确标记管理员操作范围
       await admin_operation()

   # 不要在整个请求周期都使用管理员模式
   ```

3. **验证租户权限**
   ```python
   # 在设置 RLS 之前验证用户有权访问该租户
   if not await has_tenant_permission(user, tenant_id):
       raise PermissionError("No access to this tenant")

   async with tenant_context(db, tenant_id):
       await do_query()
   ```

### ❌ 常见错误

1. **忘记设置租户上下文**
   ```python
   # 错误：没有设置 tenant_id，RLS 会阻止所有访问
   conversations = await db.execute(select(Conversation))
   # 返回空结果或报错
   ```

2. **在事务外设置上下文**
   ```python
   # 错误：SET LOCAL 只在事务内有效
   await set_current_tenant(db, tenant_id)
   # 如果 db 不在事务中，设置可能无效
   ```

3. **混淆租户上下文**
   ```python
   # 错误：在同一个 session 中切换租户
   await set_current_tenant(db, tenant_a)
   await set_current_tenant(db, tenant_b)  # 覆盖了
   # 应该使用独立的 session 或上下文管理器
   ```

## 故障排查

### 问题 1: 查询返回空结果

**原因**: 可能没有设置 `app.current_tenant_id`

**解决**:
```python
# 检查是否设置了租户ID
status = await get_rls_status(db)
print(status["current_tenant_id"])  # 应该不为 None

# 确保在查询前设置
await set_current_tenant(db, tenant_id)
```

### 问题 2: "permission denied for table"

**原因**: RLS 策略阻止了访问

**解决**:
```sql
-- 检查策略是否正确
SELECT * FROM pg_policies WHERE tablename = 'conversations';

-- 临时禁用 RLS 进行测试（谨慎使用）
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
```

### 问题 3: 管理员无法访问数据

**原因**: 没有设置 `app.is_admin = 'true'`

**解决**:
```python
# 确保启用管理员模式
await set_admin_mode(db, True)

# 或使用上下文管理器
async with admin_context(db):
    await admin_query()
```

## 与应用层隔离的对比

| 特性 | 应用层隔离 | RLS（数据库层） | 两者结合 |
|------|-----------|----------------|----------|
| 防护深度 | 单层 | 双层 | 深度防御 ✅ |
| SQL注入防护 | ❌ | ✅ | ✅ |
| 代码漏洞防护 | ❌ | ✅ | ✅ |
| 性能开销 | 低 | 低-中 | 中 |
| 开发复杂度 | 低 | 中 | 中 |
| 推荐度 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 参考资料

- [PostgreSQL RLS 官方文档](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Row Level Security 最佳实践](https://www.postgresql.org/docs/current/sql-createpolicy.html)
- [多租户架构设计](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/overview)