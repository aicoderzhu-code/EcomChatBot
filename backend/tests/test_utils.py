"""
测试工具函数
提供通用的测试辅助方法
"""
import asyncio
import json
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from faker import Faker

fake = Faker(["zh_CN"])


# ==================== ID生成器 ====================


def generate_tenant_id() -> str:
    """生成租户ID"""
    return f"TENANT_{uuid.uuid4().hex[:12].upper()}"


def generate_admin_id() -> str:
    """生成管理员ID"""
    return f"ADMIN_{uuid.uuid4().hex[:12].upper()}"


def generate_conversation_id() -> str:
    """生成对话ID"""
    return f"CONV_{uuid.uuid4().hex[:16].upper()}"


def generate_knowledge_id() -> str:
    """生成知识库ID"""
    return f"KNOW_{uuid.uuid4().hex[:12].upper()}"


def generate_order_number() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = "".join(random.choices(string.digits, k=6))
    return f"ORDER{timestamp}{random_str}"


def generate_api_key() -> str:
    """生成API Key"""
    return f"sk_live_{uuid.uuid4().hex}"


def generate_webhook_secret() -> str:
    """生成Webhook密钥"""
    return f"whsec_{uuid.uuid4().hex[:32]}"


# ==================== 测试数据生成器 ====================


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_admin(
        role: str = "super_admin", status: str = "active"
    ) -> Dict[str, Any]:
        """生成管理员数据"""
        return {
            "username": f"admin_{uuid.uuid4().hex[:8]}",
            "password": "Admin@123456",
            "email": fake.email(),
            "phone": fake.phone_number(),
            "role": role,
            "status": status,
        }

    @staticmethod
    def generate_tenant(plan: str = "free") -> Dict[str, Any]:
        """生成租户数据"""
        return {
            "company_name": fake.company(),
            "contact_name": fake.name(),
            "contact_email": fake.email(),
            "contact_phone": fake.phone_number(),
            "password": "Tenant@123456",
            "plan_type": plan,
        }

    @staticmethod
    def generate_conversation(user_id: Optional[str] = None) -> Dict[str, Any]:
        """生成对话数据"""
        return {
            "user_id": user_id or f"user_{uuid.uuid4().hex[:8]}",
            "channel": random.choice(["web", "app", "wechat", "api"]),
            "metadata": {
                "source": "test",
                "device": random.choice(["desktop", "mobile", "tablet"]),
                "browser": random.choice(["chrome", "firefox", "safari"]),
            },
        }

    @staticmethod
    def generate_message(role: str = "user") -> Dict[str, Any]:
        """生成消息数据"""
        return {
            "role": role,
            "content": fake.sentence() if role == "user" else fake.text(),
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    @staticmethod
    def generate_knowledge(category: Optional[str] = None) -> Dict[str, Any]:
        """生成知识库数据"""
        categories = ["常见问题", "产品说明", "使用指南", "售后服务", "政策条款"]
        return {
            "knowledge_type": random.choice(["faq", "product", "guide"]),
            "title": fake.sentence(),
            "content": fake.text(),
            "category": category or random.choice(categories),
            "tags": [fake.word() for _ in range(3)],
            "source": "manual",
            "priority": random.randint(1, 5),
        }

    @staticmethod
    def generate_webhook() -> Dict[str, Any]:
        """生成Webhook数据"""
        events = [
            "conversation.created",
            "conversation.closed",
            "message.sent",
            "payment.success",
        ]
        return {
            "name": f"Webhook_{uuid.uuid4().hex[:8]}",
            "endpoint_url": f"https://example.com/webhook/{uuid.uuid4().hex[:8]}",
            "events": random.sample(events, k=random.randint(1, 3)),
            "secret": generate_webhook_secret(),
        }

    @staticmethod
    def generate_model_config(provider: str = "openai") -> Dict[str, Any]:
        """生成模型配置数据"""
        providers_models = {
            "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            "zhipuai": ["glm-4-flash", "glm-4", "glm-3-turbo"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet"],
        }
        return {
            "provider": provider,
            "model_name": random.choice(providers_models.get(provider, ["gpt-3.5-turbo"])),
            "api_key": f"sk_test_{uuid.uuid4().hex}",
            "api_base": f"https://api.{provider}.com/v1",
            "temperature": round(random.uniform(0.5, 1.0), 1),
            "max_tokens": random.choice([1000, 2000, 4000]),
            "use_case": random.choice(["chat", "embedding", "completion"]),
            "is_default": False,
        }

    @staticmethod
    def generate_payment_order(plan: str = "basic") -> Dict[str, Any]:
        """生成支付订单数据"""
        return {
            "plan_type": plan,
            "duration_months": random.choice([1, 3, 6, 12]),
            "payment_type": random.choice(["pc", "mobile"]),
            "subscription_type": random.choice(["new", "renewal", "upgrade"]),
            "description": f"订阅{plan}套餐",
        }


# ==================== 断言辅助函数 ====================


class AssertHelper:
    """断言辅助类"""

    @staticmethod
    def assert_response_success(response, expected_status: int = 200):
        """断言API响应成功"""
        assert (
            response.status_code == expected_status
        ), f"期望状态码 {expected_status}, 实际 {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("success") is not False, f"响应不成功: {data}"
        return data

    @staticmethod
    def assert_response_error(response, expected_status: int = 400):
        """断言API响应错误"""
        assert response.status_code == expected_status, f"期望状态码 {expected_status}, 实际 {response.status_code}"

        data = response.json()
        assert data.get("success") is False or "error" in data, "响应应该包含错误信息"
        return data

    @staticmethod
    def assert_pagination(data: Dict, page: int = 1, size: int = 20):
        """断言分页数据"""
        assert "total" in data, "缺少total字段"
        assert "page" in data, "缺少page字段"
        assert "size" in data, "缺少size字段"
        assert "items" in data, "缺少items字段"
        assert data["page"] == page, f"page不匹配: {data['page']} != {page}"
        assert isinstance(data["items"], list), "items应该是列表"

    @staticmethod
    def assert_has_keys(data: Dict, required_keys: List[str]):
        """断言包含必需的键"""
        missing_keys = set(required_keys) - set(data.keys())
        assert not missing_keys, f"缺少必需的键: {missing_keys}"

    @staticmethod
    def assert_uuid_format(value: str, prefix: Optional[str] = None):
        """断言UUID格式"""
        if prefix:
            assert value.startswith(prefix), f"ID应该以{prefix}开头"

        # 去掉前缀后验证UUID格式
        uuid_part = value.split("_")[-1] if "_" in value else value
        try:
            uuid.UUID(hex=uuid_part, version=4)
        except ValueError:
            assert False, f"无效的UUID格式: {value}"

    @staticmethod
    def assert_datetime_format(value: str):
        """断言日期时间格式"""
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            assert False, f"无效的日期时间格式: {value}"

    @staticmethod
    def assert_email_format(value: str):
        """断言邮箱格式"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        assert re.match(pattern, value), f"无效的邮箱格式: {value}"


# ==================== 异步测试辅助 ====================


async def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "条件未满足",
):
    """等待条件满足"""
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    raise TimeoutError(error_message)


async def retry_async(
    func, max_attempts: int = 3, delay: float = 1.0, exceptions=(Exception,)
):
    """异步重试装饰器"""
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(delay)


# ==================== 数据清理辅助 ====================


class CleanupHelper:
    """数据清理辅助类"""

    def __init__(self, db_session):
        self.db_session = db_session
        self.created_ids = {
            "tenants": [],
            "admins": [],
            "conversations": [],
            "knowledge": [],
            "webhooks": [],
        }

    def track_tenant(self, tenant_id: str):
        """追踪租户ID"""
        self.created_ids["tenants"].append(tenant_id)

    def track_admin(self, admin_id: str):
        """追踪管理员ID"""
        self.created_ids["admins"].append(admin_id)

    def track_conversation(self, conversation_id: str):
        """追踪对话ID"""
        self.created_ids["conversations"].append(conversation_id)

    def track_knowledge(self, knowledge_id: str):
        """追踪知识ID"""
        self.created_ids["knowledge"].append(knowledge_id)

    async def cleanup_all(self):
        """清理所有追踪的数据"""
        # 清理租户
        for tenant_id in self.created_ids["tenants"]:
            await self._delete_tenant(tenant_id)

        # 清理管理员
        for admin_id in self.created_ids["admins"]:
            await self._delete_admin(admin_id)

        # 清理对话
        for conversation_id in self.created_ids["conversations"]:
            await self._delete_conversation(conversation_id)

        # 清理知识库
        for knowledge_id in self.created_ids["knowledge"]:
            await self._delete_knowledge(knowledge_id)

    async def _delete_tenant(self, tenant_id: str):
        """删除租户"""
        # 实现删除逻辑
        pass

    async def _delete_admin(self, admin_id: str):
        """删除管理员"""
        # 实现删除逻辑
        pass

    async def _delete_conversation(self, conversation_id: str):
        """删除对话"""
        # 实现删除逻辑
        pass

    async def _delete_knowledge(self, knowledge_id: str):
        """删除知识"""
        # 实现删除逻辑
        pass


# ==================== 性能测试辅助 ====================


class PerformanceTracker:
    """性能追踪器"""

    def __init__(self):
        self.metrics = []

    def record(self, name: str, duration: float, success: bool = True):
        """记录性能指标"""
        self.metrics.append(
            {
                "name": name,
                "duration": duration,
                "success": success,
                "timestamp": datetime.utcnow(),
            }
        )

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        filtered = self.metrics
        if name:
            filtered = [m for m in self.metrics if m["name"] == name]

        if not filtered:
            return {}

        durations = [m["duration"] for m in filtered]
        success_count = sum(1 for m in filtered if m["success"])

        return {
            "count": len(filtered),
            "success_count": success_count,
            "success_rate": success_count / len(filtered),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
        }


# ==================== Mock数据辅助 ====================


class MockDataBuilder:
    """Mock数据构建器"""

    @staticmethod
    def build_llm_response(content: str = "AI回复") -> Dict[str, Any]:
        """构建LLM响应"""
        return {
            "response": content,
            "model": "gpt-3.5-turbo",
            "input_tokens": len(content.split()) * 2,
            "output_tokens": len(content.split()),
            "total_tokens": len(content.split()) * 3,
        }

    @staticmethod
    def build_rag_results(count: int = 3) -> List[Dict[str, Any]]:
        """构建RAG检索结果"""
        return [
            {
                "knowledge_id": generate_knowledge_id(),
                "title": fake.sentence(),
                "content": fake.text(),
                "score": random.uniform(0.7, 0.99),
            }
            for _ in range(count)
        ]

    @staticmethod
    def build_payment_callback(
        order_number: str, status: str = "success"
    ) -> Dict[str, Any]:
        """构建支付回调数据"""
        return {
            "out_trade_no": order_number,
            "trade_no": f"ALIPAY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "trade_status": "TRADE_SUCCESS" if status == "success" else "TRADE_CLOSED",
            "total_amount": "99.00",
            "buyer_pay_amount": "99.00",
            "gmt_payment": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
