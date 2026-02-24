# 订阅系统字段对齐设计

**日期**: 2026-02-24
**问题**: 首次注册账号的订阅记录在前端显示缺少订阅ID和到期日期
**方案**: 方案 B — 数据库加 UUID 字段 + 全链路统一

## 问题根因

| 层级 | 期望字段 | 实际字段 | 状态 |
|------|---------|---------|------|
| 前端 TypeScript 类型 | `subscription_id` (string UUID) | 不存在 | ❌ |
| 前端 TypeScript 类型 | `end_date` | 不存在 | ❌ |
| 后端 API 响应 | — | `id` (int), `expire_at` | 字段名不匹配 |
| 数据库模型 | — | `id` (int), `expire_at` | 无 UUID 字段 |

新注册流程本身正确（Tenant + Subscription 在同一事务中创建），问题是字段命名不一致。

## 修改范围

### 1. 数据库层

**文件**: `backend/models/tenant.py`

给 `Subscription` 模型添加 `subscription_id` 字段：

```python
import uuid

subscription_id: Mapped[str] = mapped_column(
    String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
)
```

**迁移脚本**: `backend/migrations/versions/009_add_subscription_uuid.py`

- 给 `subscriptions` 表添加 `subscription_id` 列（VARCHAR 36）
- 给所有现有记录生成并填充 UUID
- 添加 UNIQUE 约束

### 2. 后端服务层

**文件**: `backend/services/tenant_service.py`

`register_tenant` 和 `create_tenant` 创建 Subscription 时显式传入 UUID：

```python
import uuid

subscription = Subscription(
    subscription_id=str(uuid.uuid4()),
    tenant_id=tenant_id,
    # ... 其他字段不变
)
```

### 3. 后端 API 层

**文件**: `backend/api/routers/admin.py`

订阅列表响应补充字段：

```python
{
    "id": subscription.id,
    "subscription_id": subscription.subscription_id,  # 新增
    "end_date": subscription.expire_at.isoformat() if subscription.expire_at else None,  # 新增别名
    "expire_at": subscription.expire_at.isoformat() if subscription.expire_at else None,  # 保留兼容
    # ... 其他字段不变
}
```

### 4. 前端层

**文件**: `frontend/src/types/admin.ts`

更新 `SubscriptionInfo` 接口，`subscription_id` 类型确认为 `string`，`end_date` 字段确认存在。

**文件**: `frontend/src/app/(admin)/subscriptions/page.tsx`

无需改动（`rowKey="subscription_id"` 和 `dataIndex: 'end_date'` 已正确，等后端数据到位即可）。

## 影响评估

- 需要数据库迁移（低风险，只加列不改现有列）
- 现有 API 消费方不受影响（`expire_at` 保留兼容）
- 新注册账号自动获得 UUID
