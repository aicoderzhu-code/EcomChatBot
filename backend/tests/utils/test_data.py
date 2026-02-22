"""
测试数据生成器
"""
import time
import uuid
from typing import List, Dict, Any
from faker import Faker

fake = Faker("zh_CN")


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_tenant(prefix: str = "auto_test_") -> Dict[str, Any]:
        """生成测试租户数据"""
        # 使用UUID确保唯一性
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time())
        return {
            "company_name": f"{prefix}公司_{unique_id}",
            "contact_name": fake.name(),
            "contact_email": f"test_{unique_id}_{timestamp}@example.com",
            "contact_phone": fake.phone_number(),
            "password": "Test@123456",
        }

    @staticmethod
    def generate_user(index: int = 1) -> Dict[str, str]:
        """生成测试用户数据"""
        channels = ["web", "app", "wechat", "mobile"]
        unique_id = str(uuid.uuid4())[:8]
        return {
            "user_id": f"test_user_{unique_id}_{index:03d}",
            "channel": channels[index % len(channels)],
        }

    @staticmethod
    def generate_knowledge_item(category: str = "测试分类") -> Dict[str, Any]:
        """生成单个知识条目"""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "title": f"测试知识_{unique_id}",
            "content": fake.text(max_nb_chars=200),
            "category": category,
            "tags": ["测试", "自动化"],
            "source": "自动化测试",
        }

    @staticmethod
    def generate_knowledge_batch(count: int = 5) -> List[Dict[str, Any]]:
        """生成批量知识数据"""
        categories = ["售后服务", "物流信息", "支付相关", "会员服务", "产品咨询"]
        knowledge_items = []

        for i in range(count):
            knowledge_items.append({
                "title": f"测试知识_{i+1}",
                "content": fake.text(max_nb_chars=200),
                "category": categories[i % len(categories)],
                "tags": ["测试", f"标签{i+1}"],
                "source": "批量导入测试",
            })

        return knowledge_items

    @staticmethod
    def get_predefined_knowledge() -> List[Dict[str, Any]]:
        """获取预定义的知识库数据"""
        return [
            {
                "title": "退货政策",
                "content": "7天无理由退货，商品需保持完好，包装完整。退货运费由买家承担，质量问题由卖家承担。",
                "category": "售后服务",
                "tags": ["退货", "售后"],
                "source": "官方政策",
            },
            {
                "title": "配送说明",
                "content": "全国包邮，48小时内发货。支持顺丰、圆通、中通等快递，可指定快递公司。",
                "category": "物流信息",
                "tags": ["配送", "物流"],
                "source": "配送政策",
            },
            {
                "title": "支付方式",
                "content": "支持微信支付、支付宝、银联卡等多种支付方式，支付安全有保障。",
                "category": "支付相关",
                "tags": ["支付"],
                "source": "支付说明",
            },
            {
                "title": "会员权益",
                "content": "会员享受9折优惠，积分兑换礼品，生日专属优惠券，优先客服支持。",
                "category": "会员服务",
                "tags": ["会员", "优惠"],
                "source": "会员手册",
            },
            {
                "title": "售后保障",
                "content": "提供一年质保服务，支持全国联保。质保期内免费维修，非人为损坏免费换新。",
                "category": "售后服务",
                "tags": ["质保", "售后"],
                "source": "售后政策",
            },
        ]

    @staticmethod
    def get_conversation_messages() -> List[str]:
        """获取预定义的对话消息"""
        return [
            "你好，请问你们的退货政策是什么？",
            "我想查询一下订单物流信息",
            "有什么优惠活动吗？",
            "这个商品支持7天退货吗？",
            "配送一般需要多久？",
            "我是会员，有什么专属优惠？",
            "支付方式有哪些？",
            "能帮我推荐一款手机吗？",
            "售后服务怎么样？",
            "质保期是多久？",
        ]

    @staticmethod
    def generate_model_config(
        provider: str = "zhipuai",
        api_key: str = "",
    ) -> Dict[str, Any]:
        """生成模型配置数据"""
        configs = {
            "zhipuai": {
                "provider": "zhipuai",
                "model_name": "glm-4-flash",
                "api_key": api_key,
                "api_base": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "temperature": 0.7,
                "max_tokens": 2000,
                "use_case": "chat",
                "is_default": True,
            },
            "openai": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": api_key,
                "api_base": "https://api.openai.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000,
                "use_case": "chat",
                "is_default": True,
            },
            "deepseek": {
                "provider": "deepseek",
                "model_name": "deepseek-chat",
                "api_key": api_key,
                "api_base": "https://api.deepseek.com/v1",
                "temperature": 0.7,
                "max_tokens": 2000,
                "use_case": "chat",
                "is_default": True,
            },
            "anthropic": {
                "provider": "anthropic",
                "model_name": "claude-3-5-sonnet-20240620",
                "api_key": api_key,
                "temperature": 0.7,
                "max_tokens": 2000,
                "use_case": "chat",
                "is_default": True,
            },
        }

        return configs.get(provider, configs["zhipuai"])

    @staticmethod
    def generate_admin_credentials() -> Dict[str, str]:
        """生成管理员登录凭证"""
        return {
            "username": "admin",
            "password": "admin123",
        }
