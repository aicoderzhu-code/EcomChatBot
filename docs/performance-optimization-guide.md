# 性能优化指南

## 一、数据库索引优化

### 1.1 执行索引优化脚本

```bash
cd backend
psql -U ecom_user -d ecom_chatbot -f migrations/performance_optimization.sql
```

### 1.2 索引说明

| 索引名称 | 表名 | 作用 | 影响的查询 |
|---------|------|------|-----------|
| `idx_tenant_status_created` | tenants | 复合索引 | 租户列表、统计查询 |
| `idx_subscription_plan_status` | subscriptions | 复合索引 | 套餐分布、付费统计 |
| `idx_bill_overdue` | bills | 部分索引 | 欠费租户查询 |
| `idx_conversation_tenant_created` | conversations | 复合索引 | 活跃度统计 |

## 二、缓存策略

### 2.1 Redis缓存实现

```python
# backend/core/cache.py
import json
from functools import wraps
from typing import Any, Callable

def cache(key: str, ttl: int = 300):
    """
    Redis缓存装饰器
    
    Args:
        key: 缓存key模板，支持占位符
        ttl: 过期时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            redis = kwargs.get('redis')
            if not redis:
                return await func(*args, **kwargs)
            
            # 生成缓存key
            cache_key = key.format(**kwargs)
            
            # 尝试从缓存获取
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 写入缓存
            await redis.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator
```

### 2.2 统计数据缓存

**平台统计概览** - 缓存5分钟
```python
# backend/services/statistics_service.py
@cache(key="platform:statistics", ttl=300)
async def get_overview(self, redis=None):
    ...
```

**趋势数据** - 缓存10分钟
```python
@cache(key="platform:trends:{period}", ttl=600)
async def get_trend_statistics(self, period: str):
    ...
```

**Dashboard数据** - 缓存5分钟
```python
@cache(key="analytics:dashboard", ttl=300)
async def get_dashboard_data(self):
    ...
```

## 三、查询优化

### 3.1 避免N+1查询

**问题代码：**
```python
# 不好的做法
tenants = await db.query(Tenant).all()
for tenant in tenants:
    subscription = await db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id
    ).first()
```

**优化后：**
```python
# 使用JOIN一次查询
from sqlalchemy.orm import selectinload

stmt = select(Tenant).options(selectinload(Tenant.subscription))
result = await db.execute(stmt)
tenants = result.scalars().all()
```

### 3.2 分页查询优化

**使用游标分页替代OFFSET**
```python
# 传统分页（大偏移量时性能差）
query.offset((page - 1) * page_size).limit(page_size)

# 游标分页（性能更好）
query.where(Tenant.id > last_id).limit(page_size)
```

### 3.3 COUNT优化

**对于大表使用估算值：**
```python
# 精确COUNT（慢）
total = await db.scalar(select(func.count(Tenant.id)))

# 估算值（快）
estimate_stmt = text("""
    SELECT reltuples::bigint 
    FROM pg_class 
    WHERE relname = 'tenants'
""")
total = await db.scalar(estimate_stmt)
```

## 四、异步任务优化

### 4.1 导出大量数据

**使用后台任务：**
```python
from tasks.export_tasks import export_tenants_task

@router.get("/tenants/export-async")
async def export_tenants_async(
    admin: AdminDep,
    db: DBDep,
):
    # 创建导出任务
    task = export_tenants_task.delay(
        admin_id=admin.admin_id,
        filters={...}
    )
    
    return ApiResponse(data={
        "task_id": task.id,
        "message": "导出任务已创建，请稍后下载"
    })
```

### 4.2 批量操作优化

**使用批量UPDATE/INSERT：**
```python
# 不好的做法
for tenant_id in tenant_ids:
    tenant = await db.get(Tenant, tenant_id)
    tenant.status = "active"
    await db.commit()

# 优化后
await db.execute(
    update(Tenant)
    .where(Tenant.tenant_id.in_(tenant_ids))
    .values(status="active")
)
await db.commit()
```

## 五、监控建议

### 5.1 慢查询监控

**启用pg_stat_statements：**
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 查看最慢的10条查询
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### 5.2 API响应时间监控

**使用Prometheus监控：**
```python
from prometheus_client import Histogram

api_response_time = Histogram(
    'api_response_time_seconds',
    'API响应时间',
    ['method', 'endpoint']
)

@api_response_time.time()
async def get_statistics(...):
    ...
```

## 六、定时任务

### 6.1 预计算统计数据

**每小时预计算：**
```python
# backend/tasks/analytics_tasks.py
from celery import shared_task

@shared_task
def precompute_statistics():
    """预计算统计数据并缓存"""
    # 计算平台统计
    stats = StatisticsService(db).get_overview()
    redis.setex("platform:statistics", 3600, json.dumps(stats))
```

**Celery Beat配置：**
```python
# backend/celery_config.py
beat_schedule = {
    'precompute-statistics': {
        'task': 'tasks.analytics_tasks.precompute_statistics',
        'schedule': 3600.0,  # 每小时
    },
}
```

### 6.2 刷新物化视图

**每天凌晨刷新：**
```python
@shared_task
def refresh_materialized_views():
    """刷新物化视图"""
    db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats"))
```

## 七、性能基准

### 7.1 目标响应时间

| 接口 | 目标时间 | 当前时间 | 优化方法 |
|------|---------|---------|---------|
| `/admin/statistics/overview` | < 2s | - | Redis缓存 |
| `/admin/tenants?page=1` | < 500ms | - | 索引优化 |
| `/admin/tenants/export` | < 10s | - | 流式响应 |
| `/analytics/dashboard` | < 3s | - | 缓存+索引 |
| `/admin/tenants/overdue` | < 1s | - | 部分索引 |

### 7.2 性能测试

**使用Locust进行压测：**
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class AdminUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 登录获取token
        response = self.client.post("/api/v1/admin/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.token = response.json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_statistics(self):
        self.client.get(
            "/api/v1/admin/statistics/overview",
            headers=self.headers
        )
    
    @task(2)
    def list_tenants(self):
        self.client.get(
            "/api/v1/admin/tenants?page=1&size=20",
            headers=self.headers
        )
    
    @task(1)
    def get_dashboard(self):
        self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self.headers
        )
```

**运行压测：**
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

## 八、优化检查清单

- [x] 数据库索引已创建
- [ ] Redis缓存已配置
- [ ] 慢查询监控已启用
- [ ] N+1查询已优化
- [ ] 大数据导出使用异步任务
- [ ] 批量操作使用批量SQL
- [ ] 定时任务已配置
- [ ] 性能测试已完成
- [ ] 响应时间达标

## 九、故障排查

### 9.1 查询慢

```bash
# 查看正在运行的查询
SELECT pid, query, state, query_start 
FROM pg_stat_activity 
WHERE state = 'active';

# 终止慢查询
SELECT pg_terminate_backend(pid);
```

### 9.2 缓存问题

```bash
# 检查Redis连接
redis-cli ping

# 查看缓存key
redis-cli keys "platform:*"

# 清除缓存
redis-cli flushdb
```

### 9.3 内存问题

```bash
# 查看数据库连接数
SELECT count(*) FROM pg_stat_activity;

# 查看表大小
SELECT 
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

**维护者**: AI Assistant
**更新日期**: 2026-02-07
**版本**: v1.0
