# Line B: 计费与配额开发计划

> 负责领域: 配额管理、计费系统、账单任务、支付扩展
> 核心技能: 业务逻辑、定时任务、Celery
> 总周期: Week 1-9

---

## 一、开发线概述

### 1.1 职责范围

Line B 负责系统的计费与配额体系，包括：
- 配额检查与控制
- 套餐订阅管理
- 账单自动生成
- 用量计费
- 支付扩展（微信支付）

### 1.2 阶段规划

| 阶段 | 周期 | 主要任务 | 交付目标 |
|------|------|----------|----------|
| 第一阶段 | Week 1-2 | 配额与计费核心 | 配额检查、套餐订阅 |
| 第二阶段 | Week 3-5 | 账单任务实现 | 自动账单、续费、用量计费 |
| 第三阶段 | Week 7-9 | 高级计费功能 | 微信支付、服务降级、报表 |

### 1.3 依赖关系

```
Line B 输出 (被其他线依赖):
├── 配额检查装饰器 → Line C, D 的API使用
├── 配额事件 → Line A Webhook发布
└── 计费数据 → Line D 平台统计使用

Line B 输入 (依赖其他线):
├── Line A: 认证中间件 (获取tenant_id)
└── Line E: 用量指标数据
```

---

## 二、第一阶段：配额与计费核心 (Week 1-2)

### 2.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| B1.1 | 配额检查服务重构 | P0 | 1天 | 待开始 |
| B1.2 | 配额检查装饰器 | P0 | 1天 | 待开始 |
| B1.3 | 超限处理策略 | P0 | 1天 | 待开始 |
| B1.4 | 套餐订阅接口 | P0 | 1天 | 待开始 |
| B1.5 | 套餐升级/降级 | P1 | 1天 | 待开始 |
| B1.6 | 配额集成到现有API | P0 | 1天 | 待开始 |

### 2.2 详细设计

#### B1.1 配额检查服务重构

**文件**: `backend/services/quota_service.py`

```python
from enum import Enum
from typing import Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
import redis.asyncio as redis

class QuotaType(Enum):
    """配额类型"""
    CONVERSATION = "conversation"      # 对话次数(月)
    API_CALL = "api_call"              # API调用次数(月)
    STORAGE = "storage"                # 存储空间(MB)
    CONCURRENT = "concurrent"          # 并发会话数
    KNOWLEDGE_ITEMS = "knowledge"      # 知识库条目数

class OverLimitStrategy(Enum):
    """超限处理策略"""
    REJECT = "reject"                  # 拒绝服务
    UPGRADE_PROMPT = "upgrade_prompt"  # 提示升级
    PAY_AS_YOU_GO = "pay_as_you_go"    # 按量付费

@dataclass
class QuotaCheckResult:
    """配额检查结果"""
    allowed: bool
    quota_type: QuotaType
    used: int
    limit: int
    remaining: int
    strategy: OverLimitStrategy = None
    message: str = None

@dataclass
class QuotaConfig:
    """套餐配额配置"""
    conversation_quota: int      # 月对话次数
    api_quota: int               # 月API调用次数
    storage_quota: int           # 存储空间(MB)
    concurrent_quota: int        # 并发会话数
    knowledge_quota: int         # 知识库条目数
    over_limit_strategy: OverLimitStrategy

# 套餐配额定义
PLAN_QUOTAS = {
    "free": QuotaConfig(
        conversation_quota=100,
        api_quota=1000,
        storage_quota=100,      # 100MB
        concurrent_quota=1,
        knowledge_quota=100,
        over_limit_strategy=OverLimitStrategy.UPGRADE_PROMPT
    ),
    "basic": QuotaConfig(
        conversation_quota=1000,
        api_quota=10000,
        storage_quota=1024,     # 1GB
        concurrent_quota=5,
        knowledge_quota=1000,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
    "professional": QuotaConfig(
        conversation_quota=10000,
        api_quota=100000,
        storage_quota=10240,    # 10GB
        concurrent_quota=20,
        knowledge_quota=10000,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
    "enterprise": QuotaConfig(
        conversation_quota=-1,   # 无限制
        api_quota=-1,
        storage_quota=102400,   # 100GB
        concurrent_quota=100,
        knowledge_quota=-1,
        over_limit_strategy=OverLimitStrategy.PAY_AS_YOU_GO
    ),
}

class QuotaService:
    """配额服务"""

    def __init__(self, db: Session, redis: redis.Redis):
        self.db = db
        self.redis = redis

    async def check_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """
        检查配额是否足够

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 请求消耗的数量

        Returns:
            QuotaCheckResult: 检查结果
        """
        # 获取租户订阅和配额配置
        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan, PLAN_QUOTAS["free"])

        # 获取配额限制
        limit = self._get_quota_limit(quota_config, quota_type)

        # 无限制(-1)直接通过
        if limit == -1:
            return QuotaCheckResult(
                allowed=True,
                quota_type=quota_type,
                used=0,
                limit=-1,
                remaining=-1
            )

        # 获取当前用量
        used = await self._get_current_usage(tenant_id, quota_type)
        remaining = max(0, limit - used)

        # 检查是否超限
        if used + amount > limit:
            return QuotaCheckResult(
                allowed=False,
                quota_type=quota_type,
                used=used,
                limit=limit,
                remaining=remaining,
                strategy=quota_config.over_limit_strategy,
                message=self._get_over_limit_message(quota_type, quota_config)
            )

        return QuotaCheckResult(
            allowed=True,
            quota_type=quota_type,
            used=used,
            limit=limit,
            remaining=remaining - amount
        )

    async def consume_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> bool:
        """
        消耗配额

        Args:
            tenant_id: 租户ID
            quota_type: 配额类型
            amount: 消耗数量

        Returns:
            bool: 是否成功
        """
        # 使用Redis原子操作
        key = self._get_usage_key(tenant_id, quota_type)
        new_value = await self.redis.incrby(key, amount)

        # 设置过期时间(月末过期)
        ttl = await self.redis.ttl(key)
        if ttl == -1:  # 没有设置过期时间
            expire_at = self._get_month_end()
            await self.redis.expireat(key, expire_at)

        return True

    async def check_and_consume(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """
        检查并消耗配额(原子操作)

        使用Redis Lua脚本确保原子性
        """
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local amount = tonumber(ARGV[2])
        local expire_at = tonumber(ARGV[3])

        -- 无限制直接通过
        if limit == -1 then
            return {1, 0, -1}
        end

        local current = tonumber(redis.call('GET', key) or 0)

        -- 检查是否超限
        if current + amount > limit then
            return {0, current, limit}
        end

        -- 消耗配额
        local new_value = redis.call('INCRBY', key, amount)

        -- 设置过期时间
        if redis.call('TTL', key) == -1 then
            redis.call('EXPIREAT', key, expire_at)
        end

        return {1, new_value, limit}
        """

        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan, PLAN_QUOTAS["free"])
        limit = self._get_quota_limit(quota_config, quota_type)

        key = self._get_usage_key(tenant_id, quota_type)
        expire_at = int(self._get_month_end().timestamp())

        result = await self.redis.eval(
            lua_script,
            1,
            key,
            limit,
            amount,
            expire_at
        )

        allowed, used, limit = result

        if not allowed:
            return QuotaCheckResult(
                allowed=False,
                quota_type=quota_type,
                used=used,
                limit=limit,
                remaining=0,
                strategy=quota_config.over_limit_strategy,
                message=self._get_over_limit_message(quota_type, quota_config)
            )

        return QuotaCheckResult(
            allowed=True,
            quota_type=quota_type,
            used=used,
            limit=limit,
            remaining=max(0, limit - used)
        )

    async def get_quota_status(
        self,
        tenant_id: str
    ) -> dict:
        """
        获取租户所有配额状态

        Returns:
            {
                "conversation": {"used": 50, "limit": 100, "percentage": 50},
                "api_call": {...},
                ...
            }
        """
        subscription = await self._get_subscription(tenant_id)
        quota_config = PLAN_QUOTAS.get(subscription.plan, PLAN_QUOTAS["free"])

        status = {}
        for quota_type in QuotaType:
            limit = self._get_quota_limit(quota_config, quota_type)
            used = await self._get_current_usage(tenant_id, quota_type)

            if limit == -1:
                percentage = 0
            else:
                percentage = round(used / limit * 100, 2) if limit > 0 else 0

            status[quota_type.value] = {
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used) if limit != -1 else -1,
                "percentage": percentage
            }

        return status

    async def reset_monthly_quota(self, tenant_id: str):
        """重置月度配额(每月1日调用)"""
        for quota_type in [QuotaType.CONVERSATION, QuotaType.API_CALL]:
            key = self._get_usage_key(tenant_id, quota_type)
            await self.redis.delete(key)

    async def adjust_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        adjustment: int,
        reason: str
    ):
        """
        调整配额(管理员操作)

        Args:
            adjustment: 正数增加,负数减少
            reason: 调整原因
        """
        # 记录到数据库
        log = QuotaAdjustmentLog(
            tenant_id=tenant_id,
            quota_type=quota_type.value,
            adjustment=adjustment,
            reason=reason,
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        await self.db.commit()

        # 更新Redis
        key = self._get_usage_key(tenant_id, quota_type)
        if adjustment < 0:
            await self.redis.decrby(key, abs(adjustment))
        else:
            # 正数调整意味着增加额度,需要减少已用量
            current = int(await self.redis.get(key) or 0)
            new_value = max(0, current - adjustment)
            await self.redis.set(key, new_value)

    def _get_usage_key(self, tenant_id: str, quota_type: QuotaType) -> str:
        """获取Redis用量key"""
        month = datetime.now().strftime("%Y%m")
        return f"quota:{tenant_id}:{quota_type.value}:{month}"

    def _get_quota_limit(self, config: QuotaConfig, quota_type: QuotaType) -> int:
        """获取配额限制"""
        mapping = {
            QuotaType.CONVERSATION: config.conversation_quota,
            QuotaType.API_CALL: config.api_quota,
            QuotaType.STORAGE: config.storage_quota,
            QuotaType.CONCURRENT: config.concurrent_quota,
            QuotaType.KNOWLEDGE_ITEMS: config.knowledge_quota,
        }
        return mapping.get(quota_type, 0)

    async def _get_current_usage(self, tenant_id: str, quota_type: QuotaType) -> int:
        """获取当前用量"""
        key = self._get_usage_key(tenant_id, quota_type)
        value = await self.redis.get(key)
        return int(value) if value else 0

    async def _get_subscription(self, tenant_id: str):
        """获取订阅信息(带缓存)"""
        cache_key = f"subscription:{tenant_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        subscription = await self.db.execute(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        )
        subscription = subscription.scalar_one_or_none()

        if subscription:
            await self.redis.setex(cache_key, 300, json.dumps({
                "plan": subscription.plan,
                "status": subscription.status
            }))

        return subscription

    def _get_month_end(self) -> datetime:
        """获取本月最后一天"""
        today = date.today()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return datetime.combine(next_month, datetime.min.time())

    def _get_over_limit_message(
        self,
        quota_type: QuotaType,
        config: QuotaConfig
    ) -> str:
        """获取超限提示消息"""
        messages = {
            QuotaType.CONVERSATION: "本月对话次数已用完",
            QuotaType.API_CALL: "本月API调用次数已用完",
            QuotaType.STORAGE: "存储空间已用完",
            QuotaType.CONCURRENT: "并发会话数已达上限",
            QuotaType.KNOWLEDGE_ITEMS: "知识库条目数已达上限",
        }

        base_msg = messages.get(quota_type, "配额已用完")

        if config.over_limit_strategy == OverLimitStrategy.UPGRADE_PROMPT:
            return f"{base_msg}，请升级套餐获取更多额度"
        elif config.over_limit_strategy == OverLimitStrategy.PAY_AS_YOU_GO:
            return f"{base_msg}，超出部分将按量计费"
        else:
            return base_msg
```

---

#### B1.2 配额检查装饰器

**文件**: `backend/api/middleware/quota.py` (新建)

```python
from functools import wraps
from fastapi import HTTPException, Request
from typing import Callable, Optional

def check_quota(
    quota_type: QuotaType,
    amount: int = 1,
    get_amount: Callable = None
):
    """
    配额检查装饰器

    用法:
    @router.post("/conversation/create")
    @check_quota(QuotaType.CONVERSATION)
    async def create_conversation(...):
        pass

    # 动态数量
    @router.post("/knowledge/batch-import")
    @check_quota(QuotaType.KNOWLEDGE_ITEMS, get_amount=lambda req: len(req.items))
    async def batch_import(...):
        pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取request对象
            request: Request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # 获取tenant_id
            tenant_id = getattr(request.state, "tenant_id", None)
            if not tenant_id:
                raise HTTPException(status_code=401, detail="未认证")

            # 计算数量
            actual_amount = amount
            if get_amount:
                # 从请求体获取
                body = kwargs.get("request_body") or kwargs.get("body")
                if body:
                    actual_amount = get_amount(body)

            # 获取配额服务
            quota_service: QuotaService = request.app.state.quota_service

            # 检查并消耗配额
            result = await quota_service.check_and_consume(
                tenant_id,
                quota_type,
                actual_amount
            )

            if not result.allowed:
                # 根据策略返回不同响应
                if result.strategy == OverLimitStrategy.UPGRADE_PROMPT:
                    raise HTTPException(
                        status_code=402,  # Payment Required
                        detail={
                            "code": "QUOTA_EXCEEDED",
                            "message": result.message,
                            "quota_type": quota_type.value,
                            "used": result.used,
                            "limit": result.limit,
                            "upgrade_url": "/pricing"
                        }
                    )
                elif result.strategy == OverLimitStrategy.PAY_AS_YOU_GO:
                    # 按量付费模式,记录超额使用
                    await quota_service.record_overage(
                        tenant_id,
                        quota_type,
                        actual_amount
                    )
                    # 继续执行
                else:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "code": "QUOTA_EXCEEDED",
                            "message": result.message,
                            "quota_type": quota_type.value,
                            "used": result.used,
                            "limit": result.limit
                        }
                    )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator

class ConcurrentQuotaManager:
    """并发配额管理器"""

    def __init__(self, redis: Redis, quota_service: QuotaService):
        self.redis = redis
        self.quota_service = quota_service

    async def acquire(self, tenant_id: str, conversation_id: str) -> bool:
        """
        获取并发槽位

        Returns:
            bool: 是否成功获取
        """
        key = f"concurrent:{tenant_id}"

        # 检查并发配额
        result = await self.quota_service.check_quota(
            tenant_id,
            QuotaType.CONCURRENT
        )

        if not result.allowed:
            return False

        # 使用Set记录活跃会话
        current_count = await self.redis.scard(key)
        if current_count >= result.limit:
            return False

        # 添加会话
        await self.redis.sadd(key, conversation_id)
        await self.redis.expire(key, 86400)  # 24小时过期(安全机制)

        return True

    async def release(self, tenant_id: str, conversation_id: str):
        """释放并发槽位"""
        key = f"concurrent:{tenant_id}"
        await self.redis.srem(key, conversation_id)

    async def get_active_count(self, tenant_id: str) -> int:
        """获取当前活跃会话数"""
        key = f"concurrent:{tenant_id}"
        return await self.redis.scard(key)
```

---

#### B1.4 套餐订阅接口

**文件**: `backend/api/routers/tenant.py` (扩展)

```python
from backend.services.subscription_service import SubscriptionService

@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_plan(
    request: SubscribeRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    subscription_service: SubscriptionService = Depends()
):
    """
    订阅套餐

    流程:
    1. 验证套餐有效性
    2. 创建支付订单(如非免费套餐)
    3. 支付成功后激活订阅
    """
    result = await subscription_service.create_subscription(
        tenant_id=tenant_id,
        plan=request.plan,
        billing_cycle=request.billing_cycle,  # monthly/yearly
        payment_method=request.payment_method
    )

    if result.requires_payment:
        return SubscriptionResponse(
            status="pending_payment",
            payment_url=result.payment_url,
            order_number=result.order_number
        )

    return SubscriptionResponse(
        status="active",
        subscription_id=result.subscription_id,
        plan=request.plan,
        start_date=result.start_date,
        end_date=result.end_date
    )

@router.put("/subscription", response_model=SubscriptionResponse)
async def change_plan(
    request: ChangePlanRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    subscription_service: SubscriptionService = Depends()
):
    """
    变更套餐(升级/降级)

    升级: 立即生效,按比例计算差价
    降级: 下个计费周期生效
    """
    result = await subscription_service.change_plan(
        tenant_id=tenant_id,
        new_plan=request.new_plan,
        effective_immediately=request.effective_immediately
    )

    return SubscriptionResponse(
        status="success",
        subscription_id=result.subscription_id,
        plan=result.new_plan,
        effective_date=result.effective_date,
        price_adjustment=result.price_adjustment
    )
```

**订阅服务**:

**文件**: `backend/services/subscription_service.py`

```python
class SubscriptionService:
    """订阅服务"""

    # 套餐价格(元/月)
    PLAN_PRICES = {
        "free": 0,
        "basic": 99,
        "professional": 299,
        "enterprise": 999,
    }

    # 年付折扣
    YEARLY_DISCOUNT = 0.83  # 约等于10个月价格

    async def create_subscription(
        self,
        tenant_id: str,
        plan: str,
        billing_cycle: str,
        payment_method: str = None
    ) -> SubscriptionResult:
        """创建订阅"""

        # 验证套餐
        if plan not in self.PLAN_PRICES:
            raise ValueError(f"无效套餐: {plan}")

        price = self.PLAN_PRICES[plan]

        # 免费套餐直接激活
        if price == 0:
            subscription = await self._create_free_subscription(tenant_id)
            return SubscriptionResult(
                requires_payment=False,
                subscription_id=str(subscription.id),
                start_date=subscription.start_date,
                end_date=subscription.end_date
            )

        # 计算价格
        if billing_cycle == "yearly":
            total_price = price * 12 * self.YEARLY_DISCOUNT
        else:
            total_price = price

        # 创建支付订单
        order = await self._create_payment_order(
            tenant_id=tenant_id,
            amount=total_price,
            description=f"{plan}套餐 - {billing_cycle}",
            metadata={
                "type": "subscription",
                "plan": plan,
                "billing_cycle": billing_cycle
            }
        )

        # 生成支付链接
        payment_url = await self._generate_payment_url(order, payment_method)

        return SubscriptionResult(
            requires_payment=True,
            payment_url=payment_url,
            order_number=order.order_number
        )

    async def change_plan(
        self,
        tenant_id: str,
        new_plan: str,
        effective_immediately: bool = False
    ) -> PlanChangeResult:
        """变更套餐"""

        current_sub = await self._get_current_subscription(tenant_id)
        if not current_sub:
            raise ValueError("当前无有效订阅")

        current_plan = current_sub.plan
        new_price = self.PLAN_PRICES[new_plan]
        current_price = self.PLAN_PRICES[current_plan]

        is_upgrade = new_price > current_price

        if is_upgrade:
            # 升级: 计算剩余天数的差价
            remaining_days = (current_sub.end_date - datetime.now()).days
            daily_diff = (new_price - current_price) / 30
            price_adjustment = daily_diff * remaining_days

            if effective_immediately:
                # 创建补差价订单
                order = await self._create_payment_order(
                    tenant_id=tenant_id,
                    amount=price_adjustment,
                    description=f"套餐升级: {current_plan} -> {new_plan}",
                    metadata={
                        "type": "upgrade",
                        "from_plan": current_plan,
                        "to_plan": new_plan
                    }
                )
                # 支付成功后自动升级
                return PlanChangeResult(
                    requires_payment=True,
                    payment_url=await self._generate_payment_url(order),
                    price_adjustment=price_adjustment
                )
            else:
                # 下个周期生效
                current_sub.next_plan = new_plan
                await self.db.commit()
                return PlanChangeResult(
                    requires_payment=False,
                    effective_date=current_sub.end_date
                )
        else:
            # 降级: 下个周期生效
            current_sub.next_plan = new_plan
            await self.db.commit()
            return PlanChangeResult(
                requires_payment=False,
                effective_date=current_sub.end_date,
                message="降级将在当前计费周期结束后生效"
            )

    async def on_payment_success(self, order_number: str):
        """支付成功回调"""
        order = await self._get_order(order_number)
        metadata = order.metadata

        if metadata["type"] == "subscription":
            await self._activate_subscription(
                tenant_id=order.tenant_id,
                plan=metadata["plan"],
                billing_cycle=metadata["billing_cycle"]
            )
        elif metadata["type"] == "upgrade":
            await self._upgrade_subscription(
                tenant_id=order.tenant_id,
                new_plan=metadata["to_plan"]
            )
        elif metadata["type"] == "renewal":
            await self._renew_subscription(
                tenant_id=order.tenant_id
            )
```

---

### 2.3 接口契约

#### 对外提供的接口

| 接口 | 类型 | 说明 | 使用方 |
|------|------|------|--------|
| `@check_quota()` | 装饰器 | 配额检查 | Line C, D |
| `QuotaService.check_quota()` | 方法 | 手动检查配额 | Line C |
| `QuotaService.get_quota_status()` | 方法 | 获取配额状态 | Line D, E |
| `ConcurrentQuotaManager` | 类 | 并发管理 | Line C |

#### API端点

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/v1/tenant/quota` | 查询 | 获取配额状态 |
| `POST /api/v1/tenant/subscribe` | 创建 | 订阅套餐 |
| `PUT /api/v1/tenant/subscription` | 更新 | 变更套餐 |
| `GET /api/v1/tenant/subscription` | 查询 | 获取订阅详情 |

---

## 三、第二阶段：账单任务实现 (Week 3-5)

### 3.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| B2.1 | 月度账单生成 | P0 | 2天 | 待开始 |
| B2.2 | 用量费用计算 | P0 | 1.5天 | 待开始 |
| B2.3 | 订阅续费处理 | P0 | 1.5天 | 待开始 |
| B2.4 | 过期订阅检查 | P1 | 1天 | 待开始 |
| B2.5 | 退款处理 | P1 | 1天 | 待开始 |
| B2.6 | 发票生成 | P2 | 1天 | 待开始 |
| B2.7 | 定时任务配置 | P0 | 0.5天 | 待开始 |

### 3.2 详细设计

#### B2.1 月度账单生成

**文件**: `backend/tasks/billing_tasks.py`

```python
from celery import shared_task
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

@shared_task(bind=True, max_retries=3)
def generate_monthly_bills(self, billing_period: str = None):
    """
    生成月度账单

    执行时间: 每月1日凌晨2:00
    """
    db = get_db_session()

    try:
        # 确定计费周期
        if billing_period is None:
            today = datetime.now()
            last_month = today - relativedelta(months=1)
            billing_period = last_month.strftime("%Y-%m")

        logger.info(f"开始生成 {billing_period} 账单")

        # 获取所有活跃租户
        tenants = db.query(Tenant).filter(
            Tenant.status == "active"
        ).all()

        success_count = 0
        fail_count = 0

        for tenant in tenants:
            try:
                bill = generate_tenant_bill(db, tenant, billing_period)
                if bill:
                    success_count += 1
                    # 发送账单通知
                    send_bill_notification.delay(str(tenant.id), str(bill.id))
            except Exception as e:
                fail_count += 1
                logger.error(f"租户 {tenant.id} 账单生成失败: {e}")

        logger.info(f"账单生成完成: 成功{success_count}, 失败{fail_count}")

        return {
            "billing_period": billing_period,
            "success": success_count,
            "failed": fail_count
        }

    except Exception as e:
        logger.error(f"账单生成任务失败: {e}")
        self.retry(exc=e, countdown=300)

    finally:
        db.close()

def generate_tenant_bill(db: Session, tenant: Tenant, period: str) -> Bill:
    """为单个租户生成账单"""

    subscription = tenant.subscription
    if not subscription:
        return None

    # 1. 基础费用
    base_fee = calculate_base_fee(subscription, period)

    # 2. 获取用量记录
    usage = get_monthly_usage(db, tenant.id, period)

    # 3. 计算超额费用
    overage_fee = calculate_overage_fee(subscription, usage)

    # 4. 应用折扣
    discount = calculate_discount(tenant, base_fee + overage_fee)

    # 5. 计算总金额
    total_amount = base_fee + overage_fee - discount

    # 6. 创建账单
    bill = Bill(
        tenant_id=tenant.id,
        billing_period=period,
        base_fee=base_fee,
        overage_fee=overage_fee,
        discount=discount,
        total_amount=total_amount,
        status="pending" if total_amount > 0 else "paid",
        due_date=datetime.now() + timedelta(days=15),  # 15天后到期
        details={
            "subscription": {
                "plan": subscription.plan,
                "monthly_price": PLAN_PRICES[subscription.plan]
            },
            "usage": {
                "conversations": usage.conversation_count,
                "api_calls": usage.api_calls,
                "storage_mb": usage.storage_used,
                "tokens": {
                    "input": usage.input_tokens,
                    "output": usage.output_tokens
                }
            },
            "overage": {
                "conversations": max(0, usage.conversation_count - subscription.conversation_quota),
                "api_calls": max(0, usage.api_calls - subscription.api_quota),
                "tokens": usage.input_tokens + usage.output_tokens
            }
        }
    )

    db.add(bill)
    db.commit()

    return bill

def calculate_overage_fee(subscription: Subscription, usage: UsageRecord) -> float:
    """
    计算超额费用

    计费规则:
    - 对话: 超出部分 ¥0.1/次
    - API调用: 超出部分 ¥0.01/次
    - Token: 输入 ¥0.001/1K, 输出 ¥0.005/1K
    - 存储: 超出部分 ¥0.5/GB/月
    """
    overage_fee = 0.0

    # 对话超额
    conversation_overage = max(0, usage.conversation_count - subscription.conversation_quota)
    overage_fee += conversation_overage * 0.1

    # API调用超额
    api_overage = max(0, usage.api_calls - subscription.api_quota)
    overage_fee += api_overage * 0.01

    # Token费用(所有Token都计费)
    overage_fee += (usage.input_tokens / 1000) * 0.001
    overage_fee += (usage.output_tokens / 1000) * 0.005

    # 存储超额
    storage_quota_mb = subscription.storage_quota
    storage_overage_mb = max(0, usage.storage_used - storage_quota_mb)
    storage_overage_gb = storage_overage_mb / 1024
    overage_fee += storage_overage_gb * 0.5

    return round(overage_fee, 2)
```

---

#### B2.3 订阅续费处理

**文件**: `backend/tasks/billing_tasks.py` (续)

```python
@shared_task(bind=True, max_retries=3)
def process_subscription_renewal(self, tenant_id: str = None):
    """
    处理订阅续费

    执行时间: 每天凌晨3:00
    """
    db = get_db_session()

    try:
        # 查询即将到期的订阅(3天内)
        expire_threshold = datetime.now() + timedelta(days=3)

        query = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date <= expire_threshold,
            Subscription.auto_renew == True
        )

        if tenant_id:
            query = query.filter(Subscription.tenant_id == tenant_id)

        subscriptions = query.all()

        for subscription in subscriptions:
            try:
                process_single_renewal(db, subscription)
            except Exception as e:
                logger.error(f"续费处理失败 {subscription.tenant_id}: {e}")

    finally:
        db.close()

def process_single_renewal(db: Session, subscription: Subscription):
    """处理单个续费"""

    tenant = subscription.tenant

    # 检查是否有待支付账单
    pending_bills = db.query(Bill).filter(
        Bill.tenant_id == tenant.id,
        Bill.status == "pending"
    ).count()

    if pending_bills > 0:
        logger.warning(f"租户 {tenant.id} 有未支付账单,跳过自动续费")
        return

    # 计算续费金额
    plan = subscription.plan
    billing_cycle = subscription.billing_cycle
    price = PLAN_PRICES[plan]

    if billing_cycle == "yearly":
        amount = price * 12 * YEARLY_DISCOUNT
    else:
        amount = price

    # 尝试自动扣款
    payment_method = tenant.default_payment_method
    if not payment_method:
        # 发送续费提醒
        send_renewal_reminder.delay(str(tenant.id))
        return

    # 创建续费订单
    order = PaymentOrder(
        tenant_id=tenant.id,
        amount=amount,
        description=f"{plan}套餐续费",
        payment_method=payment_method,
        metadata={
            "type": "renewal",
            "plan": plan,
            "billing_cycle": billing_cycle
        }
    )
    db.add(order)
    db.commit()

    # 尝试自动扣款
    try:
        result = process_auto_payment(order, payment_method)
        if result.success:
            # 延长订阅
            if billing_cycle == "yearly":
                subscription.end_date += relativedelta(years=1)
            else:
                subscription.end_date += relativedelta(months=1)

            order.status = "paid"
            db.commit()

            # 发送续费成功通知
            send_renewal_success_notification.delay(str(tenant.id))
        else:
            # 扣款失败
            order.status = "failed"
            db.commit()
            send_payment_failed_notification.delay(str(tenant.id), result.error)

    except Exception as e:
        logger.error(f"自动扣款失败: {e}")
        send_payment_failed_notification.delay(str(tenant.id), str(e))

@shared_task
def check_expiring_subscriptions():
    """
    检查即将过期的订阅

    执行时间: 每天上午10:00
    发送提醒: 7天、3天、1天
    """
    db = get_db_session()

    try:
        now = datetime.now()

        # 7天后过期
        seven_days = now + timedelta(days=7)
        expiring_7d = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date >= seven_days,
            Subscription.end_date < seven_days + timedelta(days=1),
            Subscription.auto_renew == False
        ).all()

        for sub in expiring_7d:
            send_expiring_notification.delay(str(sub.tenant_id), 7)

        # 3天后过期
        three_days = now + timedelta(days=3)
        expiring_3d = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date >= three_days,
            Subscription.end_date < three_days + timedelta(days=1),
            Subscription.auto_renew == False
        ).all()

        for sub in expiring_3d:
            send_expiring_notification.delay(str(sub.tenant_id), 3)

        # 1天后过期
        one_day = now + timedelta(days=1)
        expiring_1d = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date >= one_day,
            Subscription.end_date < one_day + timedelta(days=1),
            Subscription.auto_renew == False
        ).all()

        for sub in expiring_1d:
            send_expiring_notification.delay(str(sub.tenant_id), 1)

        # 已过期 - 执行服务降级
        expired = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date < now
        ).all()

        for sub in expired:
            handle_subscription_expired(db, sub)

    finally:
        db.close()

def handle_subscription_expired(db: Session, subscription: Subscription):
    """处理过期订阅"""

    # 标记为过期
    subscription.status = "expired"

    # 降级到免费套餐
    subscription.plan = "free"
    subscription.next_plan = None

    # 更新配额
    # 超出免费额度的数据不删除,但不能新增

    db.commit()

    # 发送通知
    send_subscription_expired_notification.delay(str(subscription.tenant_id))

    # 触发Webhook
    publish_webhook_event.delay(
        str(subscription.tenant_id),
        "subscription.expired",
        {"previous_plan": subscription.plan}
    )
```

---

#### B2.7 定时任务配置

**文件**: `backend/tasks/celery_app.py` (扩展)

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # 账单相关
    "generate-monthly-bills": {
        "task": "tasks.billing_tasks.generate_monthly_bills",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),  # 每月1日2:00
        "options": {"queue": "billing"}
    },
    "process-subscription-renewal": {
        "task": "tasks.billing_tasks.process_subscription_renewal",
        "schedule": crontab(hour=3, minute=0),  # 每天3:00
        "options": {"queue": "billing"}
    },
    "check-expiring-subscriptions": {
        "task": "tasks.billing_tasks.check_expiring_subscriptions",
        "schedule": crontab(hour=10, minute=0),  # 每天10:00
        "options": {"queue": "billing"}
    },
    "calculate-usage-charges": {
        "task": "tasks.billing_tasks.calculate_usage_charges",
        "schedule": crontab(hour=1, minute=0),  # 每天1:00
        "options": {"queue": "billing"}
    },

    # 数据清理
    "cleanup-expired-data": {
        "task": "tasks.data_tasks.cleanup_expired_data",
        "schedule": crontab(hour=4, minute=0),  # 每天4:00
        "options": {"queue": "maintenance"}
    },

    # 订单同步
    "sync-pending-orders": {
        "task": "tasks.billing_tasks.sync_pending_orders",
        "schedule": crontab(minute="*/30"),  # 每30分钟
        "options": {"queue": "payment"}
    },
}

# 配置队列
celery_app.conf.task_routes = {
    "tasks.billing_tasks.*": {"queue": "billing"},
    "tasks.payment_tasks.*": {"queue": "payment"},
    "tasks.data_tasks.*": {"queue": "maintenance"},
    "tasks.webhook_tasks.*": {"queue": "webhook"},
    "tasks.notification_tasks.*": {"queue": "notification"},
}
```

---

## 四、第三阶段：高级计费功能 (Week 7-9)

### 4.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| B3.1 | 微信支付集成 | P0 | 3天 | 待开始 |
| B3.2 | 自动续费逻辑 | P1 | 1.5天 | 待开始 |
| B3.3 | 欠费服务降级 | P1 | 1.5天 | 待开始 |
| B3.4 | 财务报表 | P2 | 2天 | 待开始 |

### 4.2 详细设计

#### B3.1 微信支付集成

**文件**: `backend/services/wechat_pay.py` (新建)

```python
import hashlib
import time
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Optional
import json

class WechatPayClient:
    """微信支付客户端"""

    def __init__(self, config: WechatPayConfig):
        self.app_id = config.app_id
        self.mch_id = config.mch_id
        self.api_key = config.api_key
        self.api_v3_key = config.api_v3_key
        self.private_key = config.private_key
        self.serial_no = config.serial_no
        self.notify_url = config.notify_url

        self.base_url = "https://api.mch.weixin.qq.com"

    async def create_native_order(
        self,
        order_number: str,
        amount: int,  # 单位:分
        description: str,
        attach: str = None
    ) -> dict:
        """
        创建Native支付订单(扫码支付)

        Returns:
            {"code_url": "weixin://..."}
        """
        url = f"{self.base_url}/v3/pay/transactions/native"

        data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": order_number,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY"
            }
        }

        if attach:
            data["attach"] = attach

        response = await self._request("POST", url, data)
        return response

    async def create_jsapi_order(
        self,
        order_number: str,
        amount: int,
        description: str,
        openid: str,
        attach: str = None
    ) -> dict:
        """
        创建JSAPI支付订单(公众号/小程序支付)

        Returns:
            {"prepay_id": "..."}
        """
        url = f"{self.base_url}/v3/pay/transactions/jsapi"

        data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": order_number,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY"
            },
            "payer": {
                "openid": openid
            }
        }

        if attach:
            data["attach"] = attach

        response = await self._request("POST", url, data)

        # 生成前端调起支付的参数
        prepay_id = response.get("prepay_id")
        return self._generate_jsapi_params(prepay_id)

    async def query_order(self, order_number: str) -> dict:
        """查询订单状态"""
        url = f"{self.base_url}/v3/pay/transactions/out-trade-no/{order_number}"
        params = {"mchid": self.mch_id}
        return await self._request("GET", url, params=params)

    async def close_order(self, order_number: str) -> bool:
        """关闭订单"""
        url = f"{self.base_url}/v3/pay/transactions/out-trade-no/{order_number}/close"
        data = {"mchid": self.mch_id}
        await self._request("POST", url, data)
        return True

    async def refund(
        self,
        order_number: str,
        refund_number: str,
        amount: int,
        total_amount: int,
        reason: str = None
    ) -> dict:
        """申请退款"""
        url = f"{self.base_url}/v3/refund/domestic/refunds"

        data = {
            "out_trade_no": order_number,
            "out_refund_no": refund_number,
            "reason": reason or "用户申请退款",
            "amount": {
                "refund": amount,
                "total": total_amount,
                "currency": "CNY"
            }
        }

        return await self._request("POST", url, data)

    def verify_notification(self, headers: dict, body: str) -> dict:
        """
        验证回调通知签名并解密

        Args:
            headers: 请求头
            body: 请求体

        Returns:
            解密后的通知内容
        """
        # 获取签名相关header
        timestamp = headers.get("Wechatpay-Timestamp")
        nonce = headers.get("Wechatpay-Nonce")
        signature = headers.get("Wechatpay-Signature")
        serial = headers.get("Wechatpay-Serial")

        # 验证签名
        message = f"{timestamp}\n{nonce}\n{body}\n"
        if not self._verify_signature(message, signature, serial):
            raise ValueError("签名验证失败")

        # 解密数据
        data = json.loads(body)
        resource = data.get("resource", {})

        decrypted = self._decrypt_resource(
            resource.get("ciphertext"),
            resource.get("nonce"),
            resource.get("associated_data")
        )

        return json.loads(decrypted)

    def _generate_signature(self, method: str, url: str, timestamp: int, nonce: str, body: str) -> str:
        """生成请求签名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        signature = self.private_key.sign(
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        import base64
        return base64.b64encode(signature).decode()

    def _decrypt_resource(self, ciphertext: str, nonce: str, associated_data: str) -> str:
        """解密回调数据"""
        import base64

        key = self.api_v3_key.encode()
        nonce = nonce.encode()
        ciphertext = base64.b64decode(ciphertext)
        associated_data = associated_data.encode() if associated_data else b""

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)

        return plaintext.decode()

    def _generate_jsapi_params(self, prepay_id: str) -> dict:
        """生成JSAPI调起支付参数"""
        timestamp = str(int(time.time()))
        nonce = self._generate_nonce()

        message = f"{self.app_id}\n{timestamp}\n{nonce}\nprepay_id={prepay_id}\n"

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        import base64

        signature = self.private_key.sign(
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return {
            "appId": self.app_id,
            "timeStamp": timestamp,
            "nonceStr": nonce,
            "package": f"prepay_id={prepay_id}",
            "signType": "RSA",
            "paySign": base64.b64encode(signature).decode()
        }

    async def _request(self, method: str, url: str, data: dict = None, params: dict = None) -> dict:
        """发送请求"""
        import aiohttp
        import uuid

        timestamp = int(time.time())
        nonce = str(uuid.uuid4()).replace("-", "")
        body = json.dumps(data) if data else ""

        signature = self._generate_signature(method, url, timestamp, nonce, body)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{self.serial_no}",signature="{signature}"'
        }

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as resp:
                    return await resp.json()
            else:
                async with session.post(url, headers=headers, data=body) as resp:
                    return await resp.json()
```

---

#### B3.3 欠费服务降级

**文件**: `backend/services/subscription_service.py` (扩展)

```python
class ServiceDegradationManager:
    """服务降级管理器"""

    # 降级策略
    DEGRADATION_LEVELS = {
        "warning": {
            "days_overdue": 0,
            "actions": ["send_warning"]
        },
        "limited": {
            "days_overdue": 7,
            "actions": ["limit_api_rate", "disable_new_features"]
        },
        "suspended": {
            "days_overdue": 15,
            "actions": ["suspend_service", "readonly_mode"]
        },
        "terminated": {
            "days_overdue": 30,
            "actions": ["terminate_service", "schedule_data_deletion"]
        }
    }

    async def check_and_degrade(self, tenant_id: str):
        """检查并执行降级"""

        tenant = await self._get_tenant(tenant_id)
        overdue_bills = await self._get_overdue_bills(tenant_id)

        if not overdue_bills:
            # 恢复服务
            if tenant.degradation_level:
                await self._restore_service(tenant)
            return

        # 计算逾期天数
        oldest_bill = min(overdue_bills, key=lambda b: b.due_date)
        days_overdue = (datetime.now() - oldest_bill.due_date).days

        # 确定降级级别
        degradation_level = self._determine_level(days_overdue)

        # 执行降级动作
        if degradation_level != tenant.degradation_level:
            await self._apply_degradation(tenant, degradation_level)

    def _determine_level(self, days_overdue: int) -> str:
        """确定降级级别"""
        level = "warning"
        for name, config in self.DEGRADATION_LEVELS.items():
            if days_overdue >= config["days_overdue"]:
                level = name
        return level

    async def _apply_degradation(self, tenant: Tenant, level: str):
        """应用降级"""
        config = self.DEGRADATION_LEVELS[level]

        for action in config["actions"]:
            await self._execute_action(tenant, action)

        tenant.degradation_level = level
        tenant.degradation_applied_at = datetime.utcnow()
        await self.db.commit()

        # 发送通知
        await self._send_degradation_notification(tenant, level)

    async def _execute_action(self, tenant: Tenant, action: str):
        """执行降级动作"""

        if action == "send_warning":
            # 发送欠费警告
            pass

        elif action == "limit_api_rate":
            # 限制API速率到10%
            await self.redis.set(
                f"rate_limit_override:{tenant.id}",
                "0.1",  # 10%
                ex=86400 * 30
            )

        elif action == "disable_new_features":
            # 禁用新功能(只保留基础功能)
            tenant.enabled_features = ["BASIC_CHAT"]

        elif action == "suspend_service":
            # 暂停服务
            tenant.status = "suspended"

        elif action == "readonly_mode":
            # 只读模式
            await self.redis.set(
                f"readonly_mode:{tenant.id}",
                "1",
                ex=86400 * 30
            )

        elif action == "terminate_service":
            # 终止服务
            tenant.status = "terminated"

        elif action == "schedule_data_deletion":
            # 计划数据删除(30天后)
            schedule_data_deletion.apply_async(
                args=[str(tenant.id)],
                countdown=86400 * 30
            )

    async def _restore_service(self, tenant: Tenant):
        """恢复服务"""

        # 清除所有限制
        await self.redis.delete(f"rate_limit_override:{tenant.id}")
        await self.redis.delete(f"readonly_mode:{tenant.id}")

        # 恢复状态
        tenant.status = "active"
        tenant.degradation_level = None
        tenant.degradation_applied_at = None

        # 恢复功能
        subscription = tenant.subscription
        if subscription:
            tenant.enabled_features = PLAN_FEATURES.get(subscription.plan, [])

        await self.db.commit()

        # 发送恢复通知
        await self._send_restoration_notification(tenant)
```

---

## 五、验收标准

### 5.1 第一阶段验收 (Week 2末)

- [ ] 配额检查装饰器可用
- [ ] 超限时返回正确错误码
- [ ] 套餐订阅流程完整
- [ ] 配额状态API正常
- [ ] 并发控制正确

### 5.2 第二阶段验收 (Week 5末)

- [ ] 月度账单自动生成
- [ ] 超额费用计算正确
- [ ] 自动续费正常
- [ ] 到期提醒发送
- [ ] 过期降级执行

### 5.3 第三阶段验收 (Week 9末)

- [ ] 微信支付可用
- [ ] 欠费降级策略生效
- [ ] 财务报表可生成
- [ ] 所有支付回调正常

---

## 六、监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `quota_check_latency` | 配额检查延迟 | P99 > 50ms |
| `quota_exceeded_rate` | 超限率 | > 5% |
| `bill_generation_success_rate` | 账单生成成功率 | < 99% |
| `payment_success_rate` | 支付成功率 | < 95% |
| `overdue_tenant_count` | 欠费租户数 | > 10 |

---

**文档维护者**: Line B负责人
**创建日期**: 2026-02-05
**版本**: v1.0
