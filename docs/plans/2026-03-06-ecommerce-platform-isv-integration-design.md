# 电商平台 ISV 模式对接设计文档

> 日期：2026-03-06
> 状态：已批准

## 1. 背景

本项目是一个 SaaS 电商智能客服系统，需要对接国内五大电商平台（拼多多、抖店、淘宝/天猫、京东、快手），采用 **ISV（服务商）模式**——我们的系统注册为各平台的服务商应用，商家只需点击授权即可完成对接，无需自行在开发者平台申请应用。

### 当前状态

项目已有拼多多和抖店的基础对接：
- `PlatformConfig` 模型存储 OAuth 凭证和店铺信息
- `BasePlatformAdapter` 抽象类定义商品/订单接口
- `PddAdapter`/`DouyinAdapter` 实现商品和订单同步
- `PinduoduoClient`/`DouyinClient` 负责 API 通信
- `PlatformMessageService` 处理 Webhook 消息
- OAuth 流程和 Webhook 端点已在 `platform.py` 路由中实现

### 目标

1. 完善现有拼多多/抖店对接
2. 新增淘宝/天猫、京东、快手三个平台
3. 全功能对接：OAuth 授权 + 客服消息 + 商品同步 + 订单同步 + 售后处理
4. 消息接入方式：Webhook 为主，轮询为补充

## 2. 架构方案：模块化扩展

在现有 `BasePlatformAdapter` 基础上扩展统一接口，创建通用的平台路由分发，用 Celery + RabbitMQ 管理 Token 刷新和消息队列。

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ 平台授权管理  │  │ 消息会话中心  │  │ 商品/订单/售后管理 │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
└─────────┼─────────────────┼───────────────────┼─────────────┘
          │                 │                   │
┌─────────┼─────────────────┼───────────────────┼─────────────┐
│         ▼                 ▼                   ▼    FastAPI   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            PlatformGateway (统一路由分发)              │   │
│  │  /platform/{platform_type}/auth                      │   │
│  │  /platform/{platform_type}/callback                  │   │
│  │  /platform/{platform_type}/webhook                   │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │          AdapterRegistry (适配器注册表)                │   │
│  │  ┌─────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌──────┐          │   │
│  │  │ PDD │ │Douyin│ │Taobao│ │ JD │ │Kuaishou│         │   │
│  │  └──┬──┘ └──┬───┘ └──┬───┘ └─┬──┘ └──┬────┘         │   │
│  │     └───────┴────────┴───────┴───────┘               │   │
│  │              ▼ BasePlatformAdapter                    │   │
│  │     (OAuth + 消息 + 商品 + 订单 + 售后)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │               Celery + RabbitMQ                       │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐  │   │
│  │  │ Token刷新   │ │ Webhook处理  │ │ 数据同步定时   │  │   │
│  │  └─────────────┘ └──────────────┘ └───────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 3. 数据模型

### 3.1 新增 PlatformApp（ISV 应用管理，全局级别）

```python
class PlatformApp(BaseModel):
    """ISV 在各电商平台注册的应用信息"""
    __tablename__ = "platform_apps"

    platform_type     # pinduoduo/douyin/taobao/jd/kuaishou (UNIQUE)
    app_name          # 应用名称
    app_key           # 应用 Key
    app_secret        # 应用 Secret（加密存储）
    callback_url      # OAuth 回调地址
    webhook_url       # Webhook 接收地址
    scopes            # JSON - 申请的权限列表
    status            # active/inactive/reviewing
    extra_config      # JSON - 平台特有配置
```

### 3.2 扩展 PlatformConfig（商家授权，租户级别）

新增字段：

```python
authorization_status  # pending/authorized/expired/revoked
scopes               # JSON - 授权权限范围
token_expires_at     # access_token 过期时间
refresh_expires_at   # refresh_token 过期时间
last_token_refresh   # 上次刷新时间
webhook_secret       # Webhook 验签密钥
platform_app_id      # FK to platform_apps
extra_config         # JSON - 平台特有配置
```

### 3.3 新增 AfterSaleRecord（售后记录）

```python
class AfterSaleRecord(TenantBaseModel):
    __tablename__ = "after_sale_records"

    platform_config_id    # FK to platform_configs
    platform_aftersale_id # 平台侧售后单号
    order_id              # FK to orders
    aftersale_type        # refund_only/return_refund/exchange
    status                # pending/processing/approved/rejected/completed/cancelled
    reason                # 售后原因
    refund_amount         # 退款金额
    buyer_id              # 买家 ID
    platform_data         # JSON
```

### 3.4 新增 WebhookEvent（事件记录，保证可靠性）

```python
class WebhookEvent(TenantBaseModel):
    __tablename__ = "webhook_events"

    event_id           # 唯一事件 ID（幂等键）
    platform_type      # 来源平台
    platform_config_id # FK
    event_type         # message/order_status/aftersale/product_change
    payload            # JSON
    status             # received/processing/processed/failed
    retry_count        # 重试次数
    error_message      # 失败原因
    processed_at       # 处理时间
```

### 模型关系

```
PlatformApp (全局，1个/平台)
    │ 1:N
    ▼
PlatformConfig (租户级别)
    ├── 1:N → Product
    ├── 1:N → Order
    ├── 1:N → AfterSaleRecord [新增]
    ├── 1:N → WebhookEvent [新增]
    └── 1:N → Conversation
```

## 4. 适配器接口

### 4.1 扩展 BasePlatformAdapter

```python
class BasePlatformAdapter(ABC):
    # ===== OAuth =====
    @abstractmethod
    def get_auth_url(self, state: str, redirect_uri: str) -> str: ...

    @abstractmethod
    async def exchange_token(self, code: str) -> TokenResult: ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenResult: ...

    # ===== 消息 =====
    @abstractmethod
    def verify_webhook(self, headers: dict, body: bytes) -> bool: ...

    @abstractmethod
    def parse_webhook_event(self, body: dict) -> list[PlatformEvent]: ...

    @abstractmethod
    async def send_message(self, conversation_id: str, content: str,
                          msg_type: str = "text") -> bool: ...

    # ===== 商品（现有） =====
    @abstractmethod
    async def fetch_products(...) -> PageResult[ProductDTO]: ...
    @abstractmethod
    async def fetch_product_detail(...) -> ProductDTO: ...

    # ===== 订单（现有） =====
    @abstractmethod
    async def fetch_orders(...) -> PageResult[OrderDTO]: ...
    @abstractmethod
    async def fetch_order_detail(...) -> OrderDTO: ...

    # ===== 售后 =====
    @abstractmethod
    async def fetch_aftersales(self, page, page_size, status) -> PageResult[AfterSaleDTO]: ...

    @abstractmethod
    async def approve_refund(self, aftersale_id: str) -> bool: ...

    @abstractmethod
    async def reject_refund(self, aftersale_id: str, reason: str) -> bool: ...
```

### 4.2 标准化事件模型

```python
class PlatformEvent:
    event_type: str       # message/order_status/aftersale/product_change
    platform_type: str
    shop_id: str
    timestamp: datetime
    raw_data: dict

class MessageEvent(PlatformEvent):
    buyer_id: str
    conversation_id: str
    content: str
    msg_type: str         # text/image/video/order_card

class OrderEvent(PlatformEvent):
    order_id: str
    old_status: str
    new_status: str

class AfterSaleEvent(PlatformEvent):
    aftersale_id: str
    order_id: str
    aftersale_type: str
    status: str
```

### 4.3 AdapterRegistry

```python
class AdapterRegistry:
    _adapters: dict[str, Type[BasePlatformAdapter]] = {}

    @classmethod
    def register(cls, platform_type: str):
        def decorator(adapter_cls):
            cls._adapters[platform_type] = adapter_cls
            return adapter_cls
        return decorator

    @classmethod
    def create(cls, config: PlatformConfig, app: PlatformApp) -> BasePlatformAdapter:
        adapter_cls = cls._adapters.get(config.platform_type)
        if not adapter_cls:
            raise ValueError(f"Unsupported platform: {config.platform_type}")
        return adapter_cls(config=config, app=app)
```

## 5. 通用路由（PlatformGateway）

```python
router = APIRouter(prefix="/platform", tags=["platform"])

@router.get("/{platform_type}/auth")
async def oauth_redirect(platform_type: str, config_id: int, ...):
    adapter = AdapterRegistry.create(config, app)
    auth_url = adapter.get_auth_url(state, redirect_uri)
    return RedirectResponse(auth_url)

@router.get("/{platform_type}/callback")
async def oauth_callback(platform_type: str, code: str, state: str, ...):
    adapter = AdapterRegistry.create(config, app)
    token_result = await adapter.exchange_token(code)
    # 保存 token 到 PlatformConfig

@router.post("/{platform_type}/webhook")
async def webhook_handler(platform_type: str, request: Request, ...):
    adapter = AdapterRegistry.create(config, app)
    if not adapter.verify_webhook(headers, body):
        raise HTTPException(403)
    events = adapter.parse_webhook_event(body)
    for event in events:
        await enqueue_webhook_event(event)  # 入队 RabbitMQ
    return {"success": True}
```

## 6. 可靠性保障

### 6.1 Webhook 消息处理流程

```
电商平台 ──POST──▶ Webhook 端点
                      │ 立即返回 200
                      ▼
              写入 webhook_events 表 (status=received)
                      │
              发送到 RabbitMQ webhook_queue
                      │
              Celery Worker 消费
              ├── 幂等检查 (event_id 去重)
              ├── 分发到 EventHandler
              └── 失败重试 (3次, 指数退避)
```

### 6.2 Token 自动刷新

```python
# Celery Beat: 每 30 分钟执行
@celery_app.task
async def refresh_expiring_tokens():
    configs = await get_expiring_configs(minutes=30)
    for config in configs:
        adapter = AdapterRegistry.create(config, app)
        try:
            new_token = await adapter.refresh_token(config.refresh_token)
            await update_token(config.id, new_token)
        except TokenRefreshError:
            await mark_authorization_expired(config.id)
            await notify_tenant_reauth(config.tenant_id, config.platform_type)
```

### 6.3 API 速率限制

基于 Redis 的令牌桶，各平台限制：

| 平台 | QPS | QPM |
|------|-----|-----|
| 拼多多 | 10 | 300 |
| 抖店 | 10 | 500 |
| 淘宝 | 40 | 2000 |
| 京东 | 20 | 600 |
| 快手 | 10 | 300 |

## 7. 各平台适配器

| 平台 | OAuth | 消息方式 | 特殊处理 |
|------|-------|---------|---------|
| 拼多多 | `pdd.pop.auth.token.create` | Webhook | MD5/HMAC 签名 |
| 抖店 | `token.create` | Webhook | HMAC-SHA256 签名 |
| 淘宝/天猫 | `taobao.top.auth.token.create` | TMC 长连接 + 轮询 | 需实现 TMC 客户端 |
| 京东 | `jd.oauth2.accessToken` | Webhook | MD5 签名，JOS 平台 |
| 快手 | OAuth2 标准 | Webhook + 轮询 | SHA256 签名 |

### 文件结构

```
backend/services/platform/
├── base_adapter.py
├── adapter_registry.py
├── rate_limiter.py
├── platform_gateway.py
├── dto.py
├── pdd/
│   ├── client.py
│   └── adapter.py
├── douyin/
│   ├── client.py
│   └── adapter.py
├── taobao/
│   ├── client.py
│   ├── adapter.py
│   └── tmc_client.py
├── jd/
│   ├── client.py
│   └── adapter.py
└── kuaishou/
    ├── client.py
    └── adapter.py
```

## 8. 前端设计

在 `/(dashboard)/settings` 新增「电商平台」标签页：
- 平台卡片展示（5大平台，显示授权状态）
- 已授权店铺列表（店铺名、平台、状态、到期时间）
- 店铺管理弹窗（基本信息、同步设置、AI 客服设置、授权操作）
- 售后记录展示

## 9. 实施阶段

### 阶段一：基础框架搭建
- 数据模型变更 + 迁移脚本
- BasePlatformAdapter 接口扩展
- AdapterRegistry + PlatformGateway
- 标准化 DTO 和事件模型
- 重构现有拼多多/抖店到新框架

### 阶段二：可靠性 + Token 管理
- WebhookEvent 持久化 + RabbitMQ 队列
- Celery Worker 消费 Webhook 事件
- 幂等性检查
- Token 自动刷新任务
- API 速率限制器

### 阶段三：新平台适配器
- 淘宝/天猫适配器（含 TMC）
- 京东适配器
- 快手适配器
- 售后处理逻辑
- 单元测试

### 阶段四：前端 + 集成测试
- 平台授权管理页面
- 店铺管理 UI
- 售后记录展示
- 端到端集成测试
