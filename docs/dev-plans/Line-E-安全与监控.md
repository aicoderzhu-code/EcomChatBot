# Line E: 安全与监控开发计划

> 负责领域: 安全防护、质量监控、运维体系
> 核心技能: 安全开发、Prometheus、日志系统
> 总周期: Week 1-10

---

## 一、开发线概述

### 1.1 职责范围

Line E 负责系统的安全与监控能力，包括：
- 基础安全防护（限流、敏感词、脱敏）
- 质量监控系统
- 运维监控体系（Prometheus、Grafana、Sentry）

### 1.2 阶段规划

| 阶段 | 周期 | 主要任务 | 交付目标 |
|------|------|----------|----------|
| 第一阶段 | Week 1-2 | 基础安全防护 | 限流、敏感词、脱敏 |
| 第二阶段 | Week 3-5 | 质量监控系统 | 指标采集、告警规则 |
| 第三阶段 | Week 7-10 | 监控运维体系 | Prometheus、Grafana、日志 |

### 1.3 依赖关系

```
Line E 输出 (被其他线依赖):
├── 限流中间件 → 所有Line的API使用
├── 敏感词过滤 → Line C 对话模块使用
├── 数据脱敏工具 → Line A, B, D 使用
└── 监控指标 → Line D Dashboard使用

Line E 输入 (依赖其他线):
├── Line A: 认证中间件
└── Line C: 对话数据(用于质量监控)
```

---

## 二、第一阶段：基础安全防护 (Week 1-2)

### 2.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| E1.1 | 限流中间件 | P0 | 1.5天 | 待开始 |
| E1.2 | 敏感词过滤服务 | P0 | 1天 | 待开始 |
| E1.3 | 数据脱敏工具 | P0 | 1天 | 待开始 |
| E1.4 | 输入验证增强 | P1 | 0.5天 | 待开始 |
| E1.5 | 安全日志记录 | P1 | 1天 | 待开始 |

### 2.2 详细设计

#### E1.1 限流中间件

**文件**: `backend/api/middleware/rate_limit.py` (新建)

```python
import time
import hashlib
from typing import Optional, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

class RateLimitConfig:
    """限流配置"""

    # 用户维度限流
    USER_LIMIT = 60          # 每分钟60次
    USER_WINDOW = 60         # 窗口60秒

    # IP维度限流
    IP_LIMIT = 100           # 每分钟100次
    IP_WINDOW = 60           # 窗口60秒

    # 全局维度限流
    GLOBAL_LIMIT = 10000     # 每秒10000次
    GLOBAL_WINDOW = 1        # 窗口1秒

    # API维度限流(特定API的限制)
    API_LIMITS = {
        "/api/v1/conversation/chat": (30, 60),     # 每分钟30次
        "/api/v1/ai/chat": (20, 60),               # 每分钟20次
        "/api/v1/knowledge/batch-import": (5, 60), # 每分钟5次
    }

class SlidingWindowRateLimiter:
    """滑动窗口限流器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        检查是否允许请求

        使用Redis的滑动窗口算法

        Returns:
            (allowed, remaining, reset_after)
        """
        now = time.time()
        window_start = now - window

        # Redis管道操作
        pipe = self.redis.pipeline()

        # 移除窗口外的请求记录
        pipe.zremrangebyscore(key, 0, window_start)

        # 获取当前窗口内的请求数
        pipe.zcard(key)

        # 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 设置过期时间
        pipe.expire(key, window)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # 计算重试时间
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_after = int(oldest[0][1] + window - now)
            else:
                reset_after = window

            return False, 0, reset_after

        remaining = limit - current_count - 1
        return True, remaining, window

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    # 白名单路径
    WHITELIST_PATHS = [
        "/docs",
        "/openapi.json",
        "/api/v1/health",
    ]

    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(redis_client)
        self.config = RateLimitConfig()

    async def dispatch(self, request: Request, call_next):
        # 检查白名单
        if self._is_whitelisted(request.url.path):
            return await call_next(request)

        # 获取限流key
        tenant_id = getattr(request.state, "tenant_id", None)
        client_ip = self._get_client_ip(request)

        # 1. 检查全局限流
        global_allowed, _, _ = await self.limiter.is_allowed(
            "ratelimit:global",
            self.config.GLOBAL_LIMIT,
            self.config.GLOBAL_WINDOW
        )
        if not global_allowed:
            return self._rate_limit_response("服务繁忙,请稍后重试", 1)

        # 2. 检查IP限流
        ip_key = f"ratelimit:ip:{client_ip}"
        ip_allowed, ip_remaining, ip_reset = await self.limiter.is_allowed(
            ip_key,
            self.config.IP_LIMIT,
            self.config.IP_WINDOW
        )
        if not ip_allowed:
            return self._rate_limit_response("请求过于频繁,请稍后重试", ip_reset)

        # 3. 检查用户/租户限流
        if tenant_id:
            # 检查是否有配额限流覆盖
            override = await self._get_rate_limit_override(tenant_id)
            user_limit = int(self.config.USER_LIMIT * override) if override else self.config.USER_LIMIT

            user_key = f"ratelimit:tenant:{tenant_id}"
            user_allowed, user_remaining, user_reset = await self.limiter.is_allowed(
                user_key,
                user_limit,
                self.config.USER_WINDOW
            )
            if not user_allowed:
                return self._rate_limit_response("API调用频率超限", user_reset)

        # 4. 检查API特定限流
        api_limit = self.config.API_LIMITS.get(request.url.path)
        if api_limit:
            api_key = f"ratelimit:api:{tenant_id or client_ip}:{request.url.path}"
            api_allowed, api_remaining, api_reset = await self.limiter.is_allowed(
                api_key,
                api_limit[0],
                api_limit[1]
            )
            if not api_allowed:
                return self._rate_limit_response("该接口调用频率超限", api_reset)

        # 执行请求
        response = await call_next(request)

        # 添加限流头
        response.headers["X-RateLimit-Limit"] = str(self.config.USER_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(user_remaining if tenant_id else ip_remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.config.USER_WINDOW)

        return response

    def _is_whitelisted(self, path: str) -> bool:
        return any(path.startswith(wp) for wp in self.WHITELIST_PATHS)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP(支持代理)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host

    async def _get_rate_limit_override(self, tenant_id: str) -> Optional[float]:
        """获取限流覆盖(用于欠费降级)"""
        override = await self.limiter.redis.get(f"rate_limit_override:{tenant_id}")
        return float(override) if override else None

    def _rate_limit_response(self, message: str, retry_after: int):
        """返回限流响应"""
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": message,
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after)
            }
        )
```

---

#### E1.2 敏感词过滤服务

**文件**: `backend/services/content_filter.py` (新建)

```python
import re
from typing import List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import ahocorasick

class FilterLevel(Enum):
    """过滤级别"""
    BLOCK = "block"        # 完全阻止
    REPLACE = "replace"    # 替换为***
    WARNING = "warning"    # 仅警告记录

@dataclass
class FilterResult:
    """过滤结果"""
    is_safe: bool
    filtered_text: str
    detected_words: List[str]
    filter_level: FilterLevel = None
    message: str = None

class SensitiveWordFilter:
    """敏感词过滤器"""

    def __init__(self):
        self.automaton = ahocorasick.Automaton()
        self.word_levels: dict[str, FilterLevel] = {}
        self._initialized = False

    async def load_words(self, db):
        """从数据库加载敏感词"""
        # 加载敏感词表
        words = await db.execute(
            select(SensitiveWord).where(SensitiveWord.is_active == True)
        )

        for word in words.scalars():
            self.add_word(word.word, FilterLevel(word.level))

        self._build_automaton()

    def add_word(self, word: str, level: FilterLevel = FilterLevel.REPLACE):
        """添加敏感词"""
        word_lower = word.lower()
        self.automaton.add_word(word_lower, word_lower)
        self.word_levels[word_lower] = level

    def _build_automaton(self):
        """构建AC自动机"""
        self.automaton.make_automaton()
        self._initialized = True

    def filter(self, text: str) -> FilterResult:
        """
        过滤文本

        使用AC自动机进行多模式匹配
        """
        if not self._initialized:
            return FilterResult(
                is_safe=True,
                filtered_text=text,
                detected_words=[]
            )

        text_lower = text.lower()
        detected_words = []
        highest_level = None

        # AC自动机匹配
        for end_index, word in self.automaton.iter(text_lower):
            detected_words.append(word)
            level = self.word_levels.get(word, FilterLevel.REPLACE)

            if highest_level is None or self._compare_levels(level, highest_level) > 0:
                highest_level = level

        if not detected_words:
            return FilterResult(
                is_safe=True,
                filtered_text=text,
                detected_words=[]
            )

        # 根据最高级别处理
        if highest_level == FilterLevel.BLOCK:
            return FilterResult(
                is_safe=False,
                filtered_text="",
                detected_words=detected_words,
                filter_level=FilterLevel.BLOCK,
                message="内容包含违禁词,已被阻止"
            )
        elif highest_level == FilterLevel.REPLACE:
            filtered_text = self._replace_words(text, detected_words)
            return FilterResult(
                is_safe=True,
                filtered_text=filtered_text,
                detected_words=detected_words,
                filter_level=FilterLevel.REPLACE
            )
        else:  # WARNING
            return FilterResult(
                is_safe=True,
                filtered_text=text,
                detected_words=detected_words,
                filter_level=FilterLevel.WARNING
            )

    def _replace_words(self, text: str, words: List[str]) -> str:
        """替换敏感词为***"""
        result = text
        for word in words:
            # 不区分大小写替换
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            result = pattern.sub("*" * len(word), result)
        return result

    def _compare_levels(self, l1: FilterLevel, l2: FilterLevel) -> int:
        """比较过滤级别"""
        order = {FilterLevel.WARNING: 0, FilterLevel.REPLACE: 1, FilterLevel.BLOCK: 2}
        return order[l1] - order[l2]

class ContentFilter:
    """内容过滤器(组合多种过滤策略)"""

    def __init__(
        self,
        sensitive_filter: SensitiveWordFilter,
        enable_url_filter: bool = True,
        enable_contact_filter: bool = True
    ):
        self.sensitive_filter = sensitive_filter
        self.enable_url_filter = enable_url_filter
        self.enable_contact_filter = enable_contact_filter

    async def filter(self, text: str) -> FilterResult:
        """综合过滤"""

        # 1. 敏感词过滤
        result = self.sensitive_filter.filter(text)
        if not result.is_safe:
            return result

        filtered_text = result.filtered_text
        detected = result.detected_words.copy()

        # 2. URL过滤
        if self.enable_url_filter:
            urls = self._detect_urls(filtered_text)
            if urls:
                detected.extend([f"URL:{u}" for u in urls])
                filtered_text = self._replace_urls(filtered_text)

        # 3. 联系方式过滤
        if self.enable_contact_filter:
            contacts = self._detect_contacts(filtered_text)
            if contacts:
                detected.extend([f"Contact:{c}" for c in contacts])
                # 联系方式不替换,仅记录

        return FilterResult(
            is_safe=True,
            filtered_text=filtered_text,
            detected_words=detected,
            filter_level=result.filter_level
        )

    def _detect_urls(self, text: str) -> List[str]:
        """检测URL"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)

    def _replace_urls(self, text: str) -> str:
        """替换URL"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.sub(url_pattern, "[链接已过滤]", text)

    def _detect_contacts(self, text: str) -> List[str]:
        """检测联系方式"""
        contacts = []

        # 手机号
        phone_pattern = r'1[3-9]\d{9}'
        contacts.extend(re.findall(phone_pattern, text))

        # 邮箱
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        contacts.extend(re.findall(email_pattern, text))

        # 微信号(简单匹配)
        wechat_pattern = r'微信[号:]?\s*([a-zA-Z0-9_-]{6,20})'
        contacts.extend(re.findall(wechat_pattern, text))

        return contacts
```

---

#### E1.3 数据脱敏工具

**文件**: `backend/utils/desensitize.py` (新建)

```python
import re
from typing import Any, Dict, List
from functools import wraps

class Desensitizer:
    """数据脱敏器"""

    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        手机号脱敏: 138****1234
        """
        if not phone or len(phone) != 11:
            return phone
        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def mask_email(email: str) -> str:
        """
        邮箱脱敏: t***@example.com
        """
        if not email or "@" not in email:
            return email
        username, domain = email.split("@", 1)
        if len(username) <= 1:
            return f"*@{domain}"
        return f"{username[0]}***@{domain}"

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """
        身份证脱敏: 110101********1234
        """
        if not id_card or len(id_card) not in [15, 18]:
            return id_card
        return id_card[:6] + "*" * (len(id_card) - 10) + id_card[-4:]

    @staticmethod
    def mask_bank_card(card: str) -> str:
        """
        银行卡脱敏: 6222****1234
        """
        if not card or len(card) < 8:
            return card
        return card[:4] + "****" + card[-4:]

    @staticmethod
    def mask_name(name: str) -> str:
        """
        姓名脱敏: 张*明
        """
        if not name or len(name) < 2:
            return name
        if len(name) == 2:
            return name[0] + "*"
        return name[0] + "*" * (len(name) - 2) + name[-1]

    @staticmethod
    def mask_address(address: str) -> str:
        """
        地址脱敏: 北京市朝阳区****
        """
        if not address or len(address) < 10:
            return address
        # 保留省市区,隐藏详细地址
        # 简单处理: 保留前10个字符
        return address[:10] + "****"

    @staticmethod
    def mask_order_id(order_id: str) -> str:
        """
        订单号部分脱敏: 2024****8901
        """
        if not order_id or len(order_id) < 8:
            return order_id
        return order_id[:4] + "****" + order_id[-4:]

class DataDesensitizer:
    """数据对象脱敏器"""

    # 字段名到脱敏方法的映射
    FIELD_MAPPINGS = {
        "phone": Desensitizer.mask_phone,
        "mobile": Desensitizer.mask_phone,
        "telephone": Desensitizer.mask_phone,
        "email": Desensitizer.mask_email,
        "id_card": Desensitizer.mask_id_card,
        "id_number": Desensitizer.mask_id_card,
        "identity": Desensitizer.mask_id_card,
        "bank_card": Desensitizer.mask_bank_card,
        "card_number": Desensitizer.mask_bank_card,
        "name": Desensitizer.mask_name,
        "contact_name": Desensitizer.mask_name,
        "real_name": Desensitizer.mask_name,
        "address": Desensitizer.mask_address,
        "shipping_address": Desensitizer.mask_address,
    }

    @classmethod
    def desensitize(cls, data: Any, fields: List[str] = None) -> Any:
        """
        脱敏数据对象

        Args:
            data: 字典、列表或Pydantic模型
            fields: 指定要脱敏的字段,None则自动检测

        Returns:
            脱敏后的数据
        """
        if isinstance(data, dict):
            return cls._desensitize_dict(data, fields)
        elif isinstance(data, list):
            return [cls.desensitize(item, fields) for item in data]
        elif hasattr(data, "dict"):  # Pydantic模型
            return cls._desensitize_dict(data.dict(), fields)
        else:
            return data

    @classmethod
    def _desensitize_dict(cls, data: Dict, fields: List[str] = None) -> Dict:
        """脱敏字典"""
        result = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = cls._desensitize_dict(value, fields)
            elif isinstance(value, list):
                result[key] = [cls.desensitize(item, fields) for item in value]
            elif fields and key in fields:
                # 指定字段
                mask_func = cls.FIELD_MAPPINGS.get(key, lambda x: "***")
                result[key] = mask_func(value) if value else value
            elif key in cls.FIELD_MAPPINGS:
                # 自动检测字段
                result[key] = cls.FIELD_MAPPINGS[key](value) if value else value
            else:
                result[key] = value

        return result

def desensitize_response(fields: List[str] = None):
    """
    响应脱敏装饰器

    用法:
    @router.get("/users/{id}")
    @desensitize_response(["phone", "email"])
    async def get_user(...):
        return user
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return DataDesensitizer.desensitize(result, fields)
        return wrapper
    return decorator

# 日志脱敏器
class LogDesensitizer:
    """日志脱敏器"""

    PATTERNS = [
        # 手机号
        (r'1[3-9]\d{9}', lambda m: m.group()[:3] + "****" + m.group()[-4:]),
        # 邮箱
        (r'[\w\.-]+@[\w\.-]+\.\w+', lambda m: m.group()[0] + "***@" + m.group().split("@")[1]),
        # 身份证
        (r'\d{17}[\dXx]', lambda m: m.group()[:6] + "********" + m.group()[-4:]),
        # 银行卡
        (r'\d{16,19}', lambda m: m.group()[:4] + "****" + m.group()[-4:]),
        # API Key
        (r'sk_[a-zA-Z0-9]{32,}', lambda m: m.group()[:8] + "****"),
    ]

    @classmethod
    def desensitize(cls, text: str) -> str:
        """脱敏日志文本"""
        result = text
        for pattern, replacer in cls.PATTERNS:
            result = re.sub(pattern, replacer, result)
        return result
```

---

#### E1.5 安全日志记录

**文件**: `backend/utils/security_logger.py` (新建)

```python
import logging
import json
from datetime import datetime
from typing import Optional
from fastapi import Request

class SecurityLogger:
    """安全日志记录器"""

    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
        self._setup_handler()

    def _setup_handler(self):
        """配置日志处理器"""
        handler = logging.FileHandler("logs/security.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_auth_event(
        self,
        event_type: str,
        tenant_id: Optional[str],
        success: bool,
        request: Request,
        details: dict = None
    ):
        """
        记录认证事件

        event_type: login, logout, api_key_auth, token_refresh, password_change
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"auth.{event_type}",
            "tenant_id": tenant_id,
            "success": success,
            "ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "path": request.url.path,
            "details": details or {}
        }

        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, json.dumps(log_data))

    def log_access_event(
        self,
        tenant_id: str,
        resource: str,
        action: str,
        success: bool,
        request: Request,
        details: dict = None
    ):
        """
        记录访问事件

        resource: tenant, conversation, knowledge, admin
        action: create, read, update, delete, list
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"access.{resource}.{action}",
            "tenant_id": tenant_id,
            "success": success,
            "ip": self._get_client_ip(request),
            "path": request.url.path,
            "method": request.method,
            "details": details or {}
        }

        self.logger.info(json.dumps(log_data))

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        request: Request,
        details: dict = None
    ):
        """
        记录安全事件

        event_type: rate_limit, sensitive_word, sql_injection, xss_attempt
        severity: low, medium, high, critical
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"security.{event_type}",
            "severity": severity,
            "ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "path": request.url.path,
            "method": request.method,
            "details": details or {}
        }

        level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }

        self.logger.log(level_map.get(severity, logging.WARNING), json.dumps(log_data))

    def log_data_event(
        self,
        tenant_id: str,
        event_type: str,
        data_type: str,
        record_count: int,
        request: Request
    ):
        """
        记录数据操作事件

        event_type: export, import, delete, backup
        data_type: tenant, conversation, knowledge
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"data.{event_type}",
            "tenant_id": tenant_id,
            "data_type": data_type,
            "record_count": record_count,
            "ip": self._get_client_ip(request),
            "path": request.url.path
        }

        self.logger.info(json.dumps(log_data))

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

# 全局实例
security_logger = SecurityLogger()
```

---

## 三、第二阶段：质量监控系统 (Week 3-5)

### 3.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| E2.1 | 监控指标模型 | P0 | 0.5天 | 待开始 |
| E2.2 | 指标收集服务 | P0 | 2天 | 待开始 |
| E2.3 | 响应时间监控 | P0 | 1天 | 待开始 |
| E2.4 | 解决率统计 | P1 | 1天 | 待开始 |
| E2.5 | 满意度统计 | P1 | 0.5天 | 待开始 |
| E2.6 | 监控API | P0 | 1.5天 | 待开始 |
| E2.7 | 告警规则 | P1 | 1.5天 | 待开始 |

### 3.2 详细设计

#### E2.2 指标收集服务

**文件**: `backend/services/metrics_service.py` (新建)

```python
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import redis.asyncio as redis
import json

@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = None

class MetricsService:
    """指标收集服务"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # ==================== 响应时间指标 ====================

    async def record_response_time(
        self,
        tenant_id: str,
        conversation_id: str,
        response_time_ms: int,
        endpoint: str = "chat"
    ):
        """记录响应时间"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 租户级别
        tenant_key = f"metrics:response_time:{tenant_id}:{today}"
        await self.redis.lpush(tenant_key, response_time_ms)
        await self.redis.expire(tenant_key, 86400 * 30)  # 30天

        # 全局级别
        global_key = f"metrics:response_time:global:{today}"
        await self.redis.lpush(global_key, response_time_ms)
        await self.redis.expire(global_key, 86400 * 7)  # 7天

        # 更新实时平均值
        await self._update_realtime_avg("response_time", tenant_id, response_time_ms)

    async def get_response_time_stats(
        self,
        tenant_id: str = None,
        date: str = None
    ) -> dict:
        """获取响应时间统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        if tenant_id:
            key = f"metrics:response_time:{tenant_id}:{date}"
        else:
            key = f"metrics:response_time:global:{date}"

        times = await self.redis.lrange(key, 0, -1)
        if not times:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "count": 0}

        times = sorted([int(t) for t in times])
        count = len(times)

        return {
            "p50": self._percentile(times, 50),
            "p95": self._percentile(times, 95),
            "p99": self._percentile(times, 99),
            "avg": sum(times) / count,
            "min": times[0],
            "max": times[-1],
            "count": count
        }

    # ==================== 对话指标 ====================

    async def record_conversation_start(self, tenant_id: str, conversation_id: str):
        """记录对话开始"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 增加对话计数
        count_key = f"metrics:conversations:{tenant_id}:{today}"
        await self.redis.incr(count_key)
        await self.redis.expire(count_key, 86400 * 30)

        # 记录活跃会话
        active_key = f"metrics:active_conversations:{tenant_id}"
        await self.redis.sadd(active_key, conversation_id)
        await self.redis.expire(active_key, 86400)

    async def record_conversation_end(
        self,
        tenant_id: str,
        conversation_id: str,
        resolved: bool,
        transferred_to_human: bool = False
    ):
        """记录对话结束"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 移除活跃会话
        active_key = f"metrics:active_conversations:{tenant_id}"
        await self.redis.srem(active_key, conversation_id)

        # 统计解决情况
        if resolved:
            resolved_key = f"metrics:resolved:{tenant_id}:{today}"
            await self.redis.incr(resolved_key)
            await self.redis.expire(resolved_key, 86400 * 30)

        if transferred_to_human:
            transfer_key = f"metrics:human_transfer:{tenant_id}:{today}"
            await self.redis.incr(transfer_key)
            await self.redis.expire(transfer_key, 86400 * 30)

    async def get_conversation_stats(
        self,
        tenant_id: str,
        date: str = None
    ) -> dict:
        """获取对话统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        total = int(await self.redis.get(f"metrics:conversations:{tenant_id}:{date}") or 0)
        resolved = int(await self.redis.get(f"metrics:resolved:{tenant_id}:{date}") or 0)
        transferred = int(await self.redis.get(f"metrics:human_transfer:{tenant_id}:{date}") or 0)
        active = await self.redis.scard(f"metrics:active_conversations:{tenant_id}")

        return {
            "total": total,
            "resolved": resolved,
            "transferred_to_human": transferred,
            "active": active,
            "resolution_rate": round(resolved / total * 100, 2) if total > 0 else 0,
            "transfer_rate": round(transferred / total * 100, 2) if total > 0 else 0
        }

    # ==================== 满意度指标 ====================

    async def record_feedback(
        self,
        tenant_id: str,
        conversation_id: str,
        rating: int,  # 1-5
        comment: str = None
    ):
        """记录用户反馈"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 记录评分
        rating_key = f"metrics:ratings:{tenant_id}:{today}"
        await self.redis.lpush(rating_key, rating)
        await self.redis.expire(rating_key, 86400 * 30)

        # 记录评分分布
        dist_key = f"metrics:rating_dist:{tenant_id}:{today}"
        await self.redis.hincrby(dist_key, str(rating), 1)
        await self.redis.expire(dist_key, 86400 * 30)

    async def get_satisfaction_stats(
        self,
        tenant_id: str,
        date: str = None
    ) -> dict:
        """获取满意度统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        ratings_key = f"metrics:ratings:{tenant_id}:{date}"
        ratings = await self.redis.lrange(ratings_key, 0, -1)

        if not ratings:
            return {"avg_rating": 0, "nps": 0, "distribution": {}, "count": 0}

        ratings = [int(r) for r in ratings]
        count = len(ratings)
        avg = sum(ratings) / count

        # 获取分布
        dist_key = f"metrics:rating_dist:{tenant_id}:{date}"
        distribution = await self.redis.hgetall(dist_key)
        distribution = {k: int(v) for k, v in distribution.items()}

        # 计算NPS (Net Promoter Score)
        # 5分为推荐者,4分为中立,1-3分为贬低者
        promoters = distribution.get("5", 0)
        detractors = sum(distribution.get(str(i), 0) for i in range(1, 4))
        nps = round((promoters - detractors) / count * 100, 2) if count > 0 else 0

        return {
            "avg_rating": round(avg, 2),
            "nps": nps,
            "distribution": distribution,
            "count": count
        }

    # ==================== 辅助方法 ====================

    async def _update_realtime_avg(
        self,
        metric_name: str,
        tenant_id: str,
        value: float
    ):
        """更新实时平均值(滑动窗口)"""
        key = f"metrics:realtime:{metric_name}:{tenant_id}"

        # 使用有序集合,score为时间戳
        now = time.time()
        window = 300  # 5分钟窗口

        pipe = self.redis.pipeline()
        # 移除窗口外数据
        pipe.zremrangebyscore(key, 0, now - window)
        # 添加新数据
        pipe.zadd(key, {f"{now}:{value}": now})
        # 设置过期
        pipe.expire(key, window * 2)
        await pipe.execute()

    def _percentile(self, sorted_data: List[int], percentile: int) -> int:
        """计算百分位数"""
        if not sorted_data:
            return 0
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return int(sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f]))

    # ==================== 聚合查询 ====================

    async def get_dashboard_metrics(self, tenant_id: str = None) -> dict:
        """获取Dashboard指标"""
        today = datetime.utcnow().strftime("%Y%m%d")

        if tenant_id:
            response_stats = await self.get_response_time_stats(tenant_id, today)
            conversation_stats = await self.get_conversation_stats(tenant_id, today)
            satisfaction_stats = await self.get_satisfaction_stats(tenant_id, today)
        else:
            # 全局统计
            response_stats = await self.get_response_time_stats(None, today)
            conversation_stats = {"total": 0, "resolved": 0, "active": 0}  # 需要聚合
            satisfaction_stats = {"avg_rating": 0, "nps": 0}  # 需要聚合

        return {
            "response_time": response_stats,
            "conversations": conversation_stats,
            "satisfaction": satisfaction_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

#### E2.7 告警规则

**文件**: `backend/services/alert_service.py` (新建)

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Optional
from datetime import datetime
import asyncio

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"
    SLACK = "slack"

@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    metric: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 5  # 冷却时间,避免重复告警
    enabled: bool = True

@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    tenant_id: Optional[str]
    triggered_at: datetime

class AlertService:
    """告警服务"""

    # 预定义规则
    DEFAULT_RULES = [
        AlertRule(
            name="high_response_time",
            description="响应时间过高",
            metric="response_time_p95",
            condition="gt",
            threshold=3000,  # 3秒
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.DINGTALK, AlertChannel.EMAIL]
        ),
        AlertRule(
            name="critical_response_time",
            description="响应时间严重过高",
            metric="response_time_p99",
            condition="gt",
            threshold=5000,  # 5秒
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SMS, AlertChannel.DINGTALK]
        ),
        AlertRule(
            name="low_resolution_rate",
            description="解决率过低",
            metric="resolution_rate",
            condition="lt",
            threshold=70,  # 70%
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL]
        ),
        AlertRule(
            name="high_error_rate",
            description="错误率过高",
            metric="error_rate",
            condition="gt",
            threshold=5,  # 5%
            severity=AlertSeverity.ERROR,
            channels=[AlertChannel.DINGTALK, AlertChannel.SMS]
        ),
        AlertRule(
            name="quota_warning",
            description="配额使用率告警",
            metric="quota_usage_percentage",
            condition="gt",
            threshold=80,  # 80%
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL]
        ),
        AlertRule(
            name="quota_critical",
            description="配额即将耗尽",
            metric="quota_usage_percentage",
            condition="gt",
            threshold=95,  # 95%
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SMS, AlertChannel.EMAIL]
        ),
    ]

    def __init__(
        self,
        metrics_service,
        notification_service,
        redis
    ):
        self.metrics_service = metrics_service
        self.notification_service = notification_service
        self.redis = redis
        self.rules = {r.name: r for r in self.DEFAULT_RULES}

    async def check_alerts(self, tenant_id: str = None):
        """检查所有告警规则"""
        metrics = await self._collect_metrics(tenant_id)

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            metric_value = metrics.get(rule.metric)
            if metric_value is None:
                continue

            if self._check_condition(metric_value, rule.condition, rule.threshold):
                # 检查冷却期
                if await self._is_in_cooldown(rule_name, tenant_id):
                    continue

                # 触发告警
                alert = Alert(
                    rule_name=rule_name,
                    severity=rule.severity,
                    message=f"{rule.description}: {rule.metric}={metric_value} (阈值: {rule.threshold})",
                    metric_value=metric_value,
                    threshold=rule.threshold,
                    tenant_id=tenant_id,
                    triggered_at=datetime.utcnow()
                )

                await self._send_alert(alert, rule.channels)
                await self._set_cooldown(rule_name, tenant_id, rule.cooldown_minutes)

    async def _collect_metrics(self, tenant_id: str = None) -> dict:
        """收集当前指标"""
        metrics = {}

        # 响应时间
        response_stats = await self.metrics_service.get_response_time_stats(tenant_id)
        metrics["response_time_p50"] = response_stats["p50"]
        metrics["response_time_p95"] = response_stats["p95"]
        metrics["response_time_p99"] = response_stats["p99"]
        metrics["response_time_avg"] = response_stats["avg"]

        # 对话统计
        if tenant_id:
            conv_stats = await self.metrics_service.get_conversation_stats(tenant_id)
            metrics["resolution_rate"] = conv_stats["resolution_rate"]
            metrics["transfer_rate"] = conv_stats["transfer_rate"]

            # 配额使用率
            quota_status = await self._get_quota_usage(tenant_id)
            metrics["quota_usage_percentage"] = quota_status.get("conversation", {}).get("percentage", 0)

        return metrics

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查条件"""
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "eq": lambda v, t: v == t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
        }
        return ops.get(condition, lambda v, t: False)(value, threshold)

    async def _is_in_cooldown(self, rule_name: str, tenant_id: str = None) -> bool:
        """检查是否在冷却期"""
        key = f"alert:cooldown:{rule_name}:{tenant_id or 'global'}"
        return bool(await self.redis.get(key))

    async def _set_cooldown(self, rule_name: str, tenant_id: str, minutes: int):
        """设置冷却期"""
        key = f"alert:cooldown:{rule_name}:{tenant_id or 'global'}"
        await self.redis.setex(key, minutes * 60, "1")

    async def _send_alert(self, alert: Alert, channels: List[AlertChannel]):
        """发送告警"""
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self.notification_service.send_email(
                        subject=f"[{alert.severity.value.upper()}] {alert.rule_name}",
                        body=alert.message,
                        recipients=await self._get_alert_recipients(channel)
                    )
                elif channel == AlertChannel.SMS:
                    await self.notification_service.send_sms(
                        message=f"[告警] {alert.message}",
                        phones=await self._get_alert_recipients(channel)
                    )
                elif channel == AlertChannel.DINGTALK:
                    await self._send_dingtalk_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

    async def _send_dingtalk_alert(self, alert: Alert):
        """发送钉钉告警"""
        webhook_url = settings.DINGTALK_WEBHOOK_URL
        if not webhook_url:
            return

        color_map = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.ERROR: "#ff4d4f",
            AlertSeverity.CRITICAL: "#ff0000",
        }

        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"告警: {alert.rule_name}",
                "text": f"""### {alert.severity.value.upper()} 告警

**规则**: {alert.rule_name}

**消息**: {alert.message}

**时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

**租户**: {alert.tenant_id or '全局'}
"""
            }
        }

        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=message)

    async def _get_alert_recipients(self, channel: AlertChannel) -> List[str]:
        """获取告警接收人"""
        # 从配置或数据库获取
        return settings.ALERT_RECIPIENTS.get(channel.value, [])

    async def _get_quota_usage(self, tenant_id: str) -> dict:
        """获取配额使用情况"""
        # 调用配额服务
        from backend.services.quota_service import QuotaService
        quota_service = QuotaService(self.redis)
        return await quota_service.get_quota_status(tenant_id)
```

---

## 四、第三阶段：监控运维体系 (Week 7-10)

### 4.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| E3.1 | Prometheus集成 | P0 | 2天 | 待开始 |
| E3.2 | Grafana Dashboard | P0 | 2天 | 待开始 |
| E3.3 | Sentry集成 | P1 | 1天 | 待开始 |
| E3.4 | 健康检查接口 | P0 | 0.5天 | 待开始 |
| E3.5 | 日志结构化 | P1 | 1天 | 待开始 |
| E3.6 | 告警通知完善 | P1 | 1.5天 | 待开始 |
| E3.7 | API文档完善 | P1 | 2天 | 待开始 |

### 4.2 详细设计

#### E3.1 Prometheus集成

**文件**: `backend/utils/prometheus.py` (新建)

```python
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from starlette.responses import Response

# ==================== 指标定义 ====================

# 请求指标
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

HTTP_REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

HTTP_RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# 业务指标
ACTIVE_CONVERSATIONS = Gauge(
    'active_conversations_total',
    'Number of active conversations',
    ['tenant_id']
)

CONVERSATION_DURATION = Histogram(
    'conversation_duration_seconds',
    'Conversation duration',
    ['tenant_id'],
    buckets=[30, 60, 120, 300, 600, 1800, 3600]
)

MESSAGE_COUNT = Counter(
    'messages_total',
    'Total messages',
    ['tenant_id', 'direction']  # direction: inbound/outbound
)

# LLM指标
LLM_REQUESTS_TOTAL = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']  # status: success/error
)

LLM_REQUEST_DURATION = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

LLM_TOKENS_TOTAL = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['model', 'type']  # type: input/output
)

# RAG指标
RAG_RETRIEVAL_DURATION = Histogram(
    'rag_retrieval_duration_seconds',
    'RAG retrieval latency',
    ['tenant_id'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

RAG_RETRIEVAL_RESULTS = Histogram(
    'rag_retrieval_results_count',
    'Number of RAG retrieval results',
    ['tenant_id'],
    buckets=[0, 1, 3, 5, 10, 20]
)

# 系统指标
DB_CONNECTIONS = Gauge(
    'db_connections_total',
    'Database connections',
    ['state']  # state: active/idle
)

REDIS_CONNECTIONS = Gauge(
    'redis_connections_total',
    'Redis connections'
)

CELERY_TASKS_TOTAL = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']  # status: success/failure/retry
)

CELERY_TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0]
)

# 应用信息
APP_INFO = Info('app', 'Application information')

# ==================== 指标收集中间件 ====================

class PrometheusMiddleware:
    """Prometheus指标收集中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        start_time = time.time()

        # 创建自定义send来捕获状态码
        status_code = 500
        response_size = 0

        async def custom_send(message):
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_size += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, custom_send)
        finally:
            # 记录指标
            duration = time.time() - start_time
            method = scope["method"]
            path = scope["path"]

            # 简化路径(移除ID等动态部分)
            endpoint = self._simplify_path(path)

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            HTTP_RESPONSE_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)

    def _simplify_path(self, path: str) -> str:
        """简化路径,将动态部分替换为占位符"""
        import re
        # UUID模式
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        # 数字ID
        path = re.sub(r'/\d+', '/{id}', path)
        return path

# ==================== Metrics端点 ====================

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# ==================== 辅助函数 ====================

def record_llm_request(model: str, duration: float, tokens_in: int, tokens_out: int, success: bool):
    """记录LLM请求指标"""
    LLM_REQUESTS_TOTAL.labels(model=model, status="success" if success else "error").inc()
    LLM_REQUEST_DURATION.labels(model=model).observe(duration)
    LLM_TOKENS_TOTAL.labels(model=model, type="input").inc(tokens_in)
    LLM_TOKENS_TOTAL.labels(model=model, type="output").inc(tokens_out)

def record_rag_retrieval(tenant_id: str, duration: float, results_count: int):
    """记录RAG检索指标"""
    RAG_RETRIEVAL_DURATION.labels(tenant_id=tenant_id).observe(duration)
    RAG_RETRIEVAL_RESULTS.labels(tenant_id=tenant_id).observe(results_count)

def update_active_conversations(tenant_id: str, count: int):
    """更新活跃会话数"""
    ACTIVE_CONVERSATIONS.labels(tenant_id=tenant_id).set(count)

def init_app_info(version: str, environment: str):
    """初始化应用信息"""
    APP_INFO.info({
        'version': version,
        'environment': environment
    })
```

---

#### E3.4 健康检查接口

**文件**: `backend/api/routers/health.py` (新建)

```python
from fastapi import APIRouter, Depends
from datetime import datetime
import asyncio

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """
    基础健康检查

    用于负载均衡器/K8s探针
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/health/live")
async def liveness_check():
    """
    存活检查

    K8s livenessProbe使用
    """
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness_check(
    db = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    就绪检查

    K8s readinessProbe使用
    检查所有依赖服务
    """
    checks = {}
    is_ready = True

    # 检查数据库
    try:
        await asyncio.wait_for(
            db.execute("SELECT 1"),
            timeout=5.0
        )
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 检查Redis
    try:
        start = datetime.utcnow()
        await asyncio.wait_for(
            redis.ping(),
            timeout=5.0
        )
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        checks["redis"] = {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 检查Milvus
    try:
        from pymilvus import connections
        connections.connect(alias="health_check", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=5)
        connections.disconnect("health_check")
        checks["milvus"] = {"status": "healthy"}
    except Exception as e:
        checks["milvus"] = {"status": "unhealthy", "error": str(e)}
        is_ready = False

    # 检查Celery
    try:
        from backend.tasks.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active = inspect.active()
        checks["celery"] = {"status": "healthy", "workers": len(active) if active else 0}
    except Exception as e:
        checks["celery"] = {"status": "unhealthy", "error": str(e)}
        # Celery不可用不影响就绪状态

    status_code = 200 if is_ready else 503

    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@router.get("/health/detailed")
async def detailed_health_check(
    db = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    详细健康检查

    返回系统详细状态
    """
    import psutil
    import platform

    # 系统资源
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # 数据库连接池
    pool_status = {
        "size": db.get_bind().pool.size(),
        "checked_in": db.get_bind().pool.checkedin(),
        "checked_out": db.get_bind().pool.checkedout(),
        "overflow": db.get_bind().pool.overflow(),
    }

    # Redis连接
    redis_info = await redis.info()

    return {
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent
            }
        },
        "database": {
            "pool": pool_status
        },
        "redis": {
            "connected_clients": redis_info.get("connected_clients"),
            "used_memory_human": redis_info.get("used_memory_human"),
            "uptime_days": redis_info.get("uptime_in_days")
        },
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

#### E3.5 日志结构化

**文件**: `backend/utils/logger.py` (新建)

```python
import logging
import json
import sys
from datetime import datetime
from typing import Any
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON日志格式化器"""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        super().add_fields(log_record, record, message_dict)

        # 添加时间戳
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # 添加日志级别
        log_record["level"] = record.levelname

        # 添加来源信息
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # 添加进程/线程信息
        log_record["process_id"] = record.process
        log_record["thread_id"] = record.thread

        # 移除默认字段
        log_record.pop("levelname", None)
        log_record.pop("name", None)

def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str = None
):
    """配置日志系统"""

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    if json_format:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

class RequestLogger:
    """请求日志记录器"""

    def __init__(self, logger_name: str = "request"):
        self.logger = logging.getLogger(logger_name)

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        tenant_id: str = None,
        user_id: str = None,
        ip: str = None,
        user_agent: str = None,
        extra: dict = None
    ):
        """记录请求开始"""
        self.logger.info("Request started", extra={
            "request_id": request_id,
            "method": method,
            "path": path,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "ip": ip,
            "user_agent": user_agent,
            **(extra or {})
        })

    def log_response(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        response_size: int = None,
        extra: dict = None
    ):
        """记录请求结束"""
        level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR

        self.logger.log(level, "Request completed", extra={
            "request_id": request_id,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "response_size": response_size,
            **(extra or {})
        })

    def log_error(
        self,
        request_id: str,
        error: Exception,
        extra: dict = None
    ):
        """记录错误"""
        self.logger.error("Request error", extra={
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(extra or {})
        }, exc_info=True)

# 全局实例
request_logger = RequestLogger()
```

---

## 五、验收标准

### 5.1 第一阶段验收 (Week 2末)

- [ ] 限流正常工作,超限返回429
- [ ] 敏感词检测准确率 > 95%
- [ ] 数据脱敏覆盖所有敏感字段
- [ ] 安全日志完整记录

### 5.2 第二阶段验收 (Week 5末)

- [ ] 响应时间P95 < 3s
- [ ] 监控指标准确
- [ ] 告警及时触发
- [ ] 监控API响应 < 500ms

### 5.3 第三阶段验收 (Week 10末)

- [ ] Prometheus指标完整
- [ ] Grafana Dashboard可用
- [ ] Sentry错误追踪正常
- [ ] 健康检查接口可用
- [ ] 结构化日志完整

---

## 六、监控指标汇总

| 指标名称 | 类型 | 说明 | 告警阈值 |
|----------|------|------|----------|
| `http_request_duration_seconds` | Histogram | HTTP请求延迟 | P95 > 3s |
| `http_requests_total` | Counter | HTTP请求总数 | - |
| `active_conversations_total` | Gauge | 活跃会话数 | - |
| `llm_request_duration_seconds` | Histogram | LLM请求延迟 | P95 > 10s |
| `llm_tokens_total` | Counter | Token使用量 | - |
| `rag_retrieval_duration_seconds` | Histogram | RAG检索延迟 | P95 > 2s |
| `celery_tasks_total` | Counter | Celery任务数 | 失败率 > 5% |

---

**文档维护者**: Line E负责人
**创建日期**: 2026-02-05
**版本**: v1.0
