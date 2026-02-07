# 配额检查中间件使用指南

## 概述

配额检查中间件提供了灵活的配额控制功能,支持多种配额类型和超限策略。

## 配额类型

```python
class QuotaType(Enum):
    CONVERSATION = "conversation"      # 对话次数(月)
    API_CALL = "api_call"              # API调用次数(月)
    STORAGE = "storage"                # 存储空间(GB)
    CONCURRENT = "concurrent"          # 并发会话数
    KNOWLEDGE_ITEMS = "knowledge"      # 知识库条目数
```

## 超限策略

```python
class OverLimitStrategy(Enum):
    REJECT = "reject"                  # 拒绝服务
    UPGRADE_PROMPT = "upgrade_prompt"  # 提示升级
    PAY_AS_YOU_GO = "pay_as_you_go"    # 按量付费
```

## 使用方式

### 方式一:使用FastAPI依赖注入(推荐)

这是最简单的方式,适用于常见的配额检查场景。

```python
from api.middleware import ConversationQuotaDep, ConcurrentQuotaDep
from api.dependencies import DBDep

@router.post("/conversation/create")
async def create_conversation(
    data: ConversationCreate,
    tenant_id: ConversationQuotaDep,  # 自动检查对话配额
    db: DBDep,
):
    """
    创建对话 - 会自动检查对话配额
    如果配额不足,会返回 402 Payment Required
    """
    # 直接使用tenant_id,配额已检查
    pass


@router.post("/concurrent-chat")
async def concurrent_chat(
    tenant_id: ConcurrentQuotaDep,  # 检查并发配额
    db: DBDep,
):
    """检查并发会话配额"""
    pass
```

### 方式二:使用装饰器

适用于需要自定义配额数量的场景。

```python
from api.middleware import check_quota, QuotaType

@router.post("/knowledge/add")
@check_quota(QuotaType.KNOWLEDGE_ITEMS, amount=1)
async def add_knowledge(
    data: KnowledgeCreate,
    tenant_id: TenantDep,
    db: DBDep,
):
    """添加知识库条目 - 固定消耗1个配额"""
    pass


@router.post("/knowledge/batch-import")
@check_quota(
    QuotaType.KNOWLEDGE_ITEMS,
    get_amount=lambda body: len(body.items)  # 动态计算消耗数量
)
async def batch_import(
    data: BatchImportRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """批量导入知识库 - 动态配额检查"""
    pass
```

### 方式三:手动调用服务

适用于复杂的业务逻辑。

```python
from api.dependencies import QuotaServiceDep

@router.post("/custom-check")
async def custom_quota_check(
    tenant_id: TenantDep,
    quota_service: QuotaServiceDep,
):
    """手动检查配额"""
    # 检查API配额
    await quota_service.check_api_quota(tenant_id)

    # 检查存储配额
    await quota_service.check_storage_quota(tenant_id, additional_size=1.5)  # 1.5GB

    # 获取配额使用情况
    usage = await quota_service.get_quota_usage(tenant_id)

    return usage
```

## 并发配额管理

对于需要控制并发会话数的场景,使用 `ConcurrentQuotaManager`:

```python
from api.middleware import ConcurrentQuotaManager

# 在WebSocket连接时
@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    tenant_id: str,
):
    # 获取并发管理器
    concurrent_manager: ConcurrentQuotaManager = request.app.state.concurrent_quota_manager

    # 尝试获取并发槽位
    acquired = await concurrent_manager.acquire(tenant_id, conversation_id)

    if not acquired:
        await websocket.close(code=1008, reason="并发会话数已达上限")
        return

    try:
        # 处理WebSocket连接
        await websocket.accept()
        # ... 业务逻辑 ...
    finally:
        # 释放槽位
        await concurrent_manager.release(tenant_id, conversation_id)
```

## 错误处理

当配额超限时,会抛出 HTTPException:

```json
{
  "detail": {
    "code": "QUOTA_EXCEEDED",
    "message": "对话次数配额(100)已用完,请升级套餐",
    "quota_type": "conversation",
    "upgrade_url": "/pricing"
  }
}
```

状态码:
- `402 Payment Required`: 配额已用完,需要升级或付费
- `429 Too Many Requests`: 并发限制(仅用于并发配额)

## 配置

在应用启动时,中间件会自动初始化:

```python
# backend/api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ...
    # 并发配额管理器已自动注册到 app.state
    app.state.concurrent_quota_manager  # ConcurrentQuotaManager实例
    # ...
```

## 注意事项

1. **性能考虑**: 配额检查会查询数据库,对于高频API建议启用缓存
2. **并发安全**: 使用Redis保证并发配额的原子性
3. **异常处理**: 确保在finally块中释放并发槽位,避免泄漏
4. **监控告警**: 建议监控配额使用率,及时通知用户

## 下一步

- [ ] 实现Redis原子操作优化(Task #2)
- [ ] 添加配额使用率监控
- [ ] 支持自定义超限策略
- [ ] 集成Webhook通知