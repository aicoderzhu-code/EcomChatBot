# 订阅系统字段对齐 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 给 Subscription 模型添加 UUID 字段 `subscription_id`，并在 API 响应中补充 `subscription_id` 和 `end_date`，使前端显示正常。

**Architecture:** 数据库层加 `subscription_id`（UUID）字段，写迁移脚本给现有记录补充 UUID；服务层创建 Subscription 时显式传入 UUID；API 层响应补充 `subscription_id` 和 `end_date` 字段；前端 TypeScript 类型补充缺失字段。

**Tech Stack:** Python/SQLAlchemy (backend), Alembic (migrations), TypeScript/React (frontend)

---

### Task 1: 给 Subscription 模型添加 subscription_id 字段

**Files:**
- Modify: `backend/models/tenant.py:110-177`

**Step 1: 在模型文件顶部确认 uuid 已可用**

`backend/models/tenant.py` 第 4 行已有 `from datetime import datetime`，需要在同行附近添加 uuid 导入。

**Step 2: 修改 Subscription 模型，添加 subscription_id 字段**

在 `backend/models/tenant.py` 第 4 行后添加 import：

```python
import uuid
```

在 `Subscription` 类的 `tenant_id` 字段（第 121 行）之前添加：

```python
    # 订阅唯一标识
    subscription_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), comment="订阅唯一标识(UUID)"
    )
```

**Step 3: 验证模型语法**

```bash
cd backend && python -c "from models.tenant import Subscription; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add backend/models/tenant.py
git commit -m "feat: 给 Subscription 模型添加 subscription_id UUID 字段"
```

---

### Task 2: 写数据库迁移脚本

**Files:**
- Create: `backend/migrations/versions/009_add_subscription_uuid.py`

**Step 1: 创建迁移文件**

创建 `backend/migrations/versions/009_add_subscription_uuid.py`：

```python
"""add subscription_id uuid field

Revision ID: 009
Revises: 008
Create Date: 2026-02-24
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 添加列（允许 NULL，后面填充数据再加约束）
    op.add_column(
        "subscriptions",
        sa.Column("subscription_id", sa.String(36), nullable=True, comment="订阅唯一标识(UUID)"),
    )

    # 2. 给现有记录填充 UUID
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id FROM subscriptions")).fetchall()
    for row in rows:
        conn.execute(
            text("UPDATE subscriptions SET subscription_id = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": row[0]},
        )

    # 3. 改为 NOT NULL + UNIQUE
    op.alter_column("subscriptions", "subscription_id", nullable=False)
    op.create_unique_constraint("uq_subscription_id", "subscriptions", ["subscription_id"])
    op.create_index("idx_subscription_uuid", "subscriptions", ["subscription_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_subscription_uuid", table_name="subscriptions")
    op.drop_constraint("uq_subscription_id", "subscriptions", type_="unique")
    op.drop_column("subscriptions", "subscription_id")
```

**Step 2: 运行迁移**

```bash
cd backend && alembic upgrade head
```

Expected: 无报错，输出 `Running upgrade 008 -> 009`

**Step 3: 验证数据库**

```bash
cd backend && python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ.get('DATABASE_URL', 'sqlite:///./test.db'))
with engine.connect() as conn:
    rows = conn.execute(text('SELECT id, subscription_id FROM subscriptions LIMIT 3')).fetchall()
    for r in rows: print(r)
"
```

Expected: 每行都有非空的 UUID 字符串

**Step 4: Commit**

```bash
git add backend/migrations/versions/009_add_subscription_uuid.py
git commit -m "feat: 迁移脚本 009 - 给 subscriptions 表添加 subscription_id UUID 字段"
```

---

### Task 3: 服务层创建 Subscription 时传入 UUID

**Files:**
- Modify: `backend/services/tenant_service.py`

需要修改三处 `Subscription(` 调用（第 83、174、575 行），每处都加 `subscription_id=str(uuid.uuid4())`。

**Step 1: 确认文件顶部有 uuid import**

```bash
grep -n "import uuid" backend/services/tenant_service.py
```

如果没有，在文件顶部添加 `import uuid`。

**Step 2: 修改第一处（约第 83 行，免费套餐创建）**

在 `Subscription(` 的第一个参数后添加：

```python
subscription = Subscription(
    subscription_id=str(uuid.uuid4()),  # 新增
    tenant_id=tenant_id,
    plan_type="free",
    # ... 其余不变
)
```

**Step 3: 修改第二处（约第 174 行，create_tenant）**

```python
subscription = Subscription(
    subscription_id=str(uuid.uuid4()),  # 新增
    tenant_id=tenant_id,
    plan_type=tenant_data.initial_plan,
    # ... 其余不变
)
```

**Step 4: 修改第三处（约第 575 行，register_tenant trial）**

```python
subscription = Subscription(
    subscription_id=str(uuid.uuid4()),  # 新增
    tenant_id=tenant_id,
    plan_type="trial",
    # ... 其余不变
)
```

**Step 5: 验证语法**

```bash
cd backend && python -c "from services.tenant_service import TenantService; print('OK')"
```

Expected: `OK`

**Step 6: Commit**

```bash
git add backend/services/tenant_service.py
git commit -m "feat: 服务层创建 Subscription 时显式生成 subscription_id UUID"
```

---

### Task 4: API 层响应补充 subscription_id 和 end_date

**Files:**
- Modify: `backend/api/routers/admin.py:808-826`

**Step 1: 修改订阅列表响应 dict**

将第 810-826 行的 `items.append({...})` 改为：

```python
        items.append({
            "id": subscription.id,
            "subscription_id": subscription.subscription_id,  # 新增
            "tenant_id": subscription.tenant_id,
            "company_name": tenant.company_name,
            "plan_type": subscription.plan_type,
            "status": subscription.status,
            "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
            "end_date": subscription.expire_at.isoformat() if subscription.expire_at else None,  # 新增别名
            "expire_at": subscription.expire_at.isoformat() if subscription.expire_at else None,
            "auto_renew": subscription.auto_renew,
            "is_trial": subscription.is_trial,
            "conversation_quota": subscription.conversation_quota,
            "api_quota": subscription.api_quota,
            "storage_quota": subscription.storage_quota,
            "concurrent_quota": subscription.concurrent_quota,
            "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
            "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None,
        })
```

**Step 2: 验证语法**

```bash
cd backend && python -c "from api.routers.admin import router; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/api/routers/admin.py
git commit -m "feat: admin API 订阅列表响应补充 subscription_id 和 end_date 字段"
```

---

### Task 5: 前端 TypeScript 类型补充缺失字段

**Files:**
- Modify: `frontend/src/types/admin.ts:152-163`

**Step 1: 更新 SubscriptionInfo 接口**

将第 152-163 行改为：

```typescript
export interface SubscriptionInfo {
  id: number;
  subscription_id: string;
  tenant_id: string;
  company_name?: string;
  plan_type: string;
  status: SubscriptionStatus;
  start_date: string;
  end_date: string;
  expire_at: string;
  auto_renew: boolean;
  is_trial?: boolean;
  conversation_quota?: number;
  api_quota?: number;
  storage_quota?: number;
  concurrent_quota?: number;
  created_at: string;
  updated_at: string;
}
```

**Step 2: 检查 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: 无与 SubscriptionInfo 相关的错误

**Step 3: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "feat: 更新 SubscriptionInfo 类型，补充 subscription_id、end_date 等字段"
```

---

### Task 6: 端到端验证

**Step 1: 启动后端（手动在终端运行）**

```bash
cd backend && uvicorn main:app --reload
```

**Step 2: 调用订阅列表 API 验证响应**

```bash
curl -s -H "Authorization: Bearer <admin_token>" http://localhost:8000/admin/subscriptions | python -m json.tool | grep -E "subscription_id|end_date"
```

Expected: 每条记录都有 `subscription_id`（UUID 格式）和 `end_date`（ISO 日期字符串）

**Step 3: 注册新账号验证**

注册一个新租户，然后查询其订阅记录，确认 `subscription_id` 不为空。

**Step 4: 前端页面验证**

打开管理后台订阅页面，确认：
- 表格行有唯一 key（不报 React warning）
- 到期日期列正常显示
- 订阅 ID 列正常显示
