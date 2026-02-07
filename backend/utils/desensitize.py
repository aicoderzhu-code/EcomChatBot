"""
数据脱敏工具
"""
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
        (r"1[3-9]\d{9}", lambda m: m.group()[:3] + "****" + m.group()[-4:]),
        # 邮箱
        (
            r"[\w\.-]+@[\w\.-]+\.\w+",
            lambda m: m.group()[0] + "***@" + m.group().split("@")[1],
        ),
        # 身份证
        (r"\d{17}[\dXx]", lambda m: m.group()[:6] + "********" + m.group()[-4:]),
        # 银行卡
        (r"\d{16,19}", lambda m: m.group()[:4] + "****" + m.group()[-4:]),
        # API Key
        (r"sk_[a-zA-Z0-9]{32,}", lambda m: m.group()[:8] + "****"),
    ]

    @classmethod
    def desensitize(cls, text: str) -> str:
        """脱敏日志文本"""
        result = text
        for pattern, replacer in cls.PATTERNS:
            result = re.sub(pattern, replacer, result)
        return result
