"""
内容安全过滤器
"""
from typing import List
import re


class ContentFilter:
    """内容安全过滤器"""

    # 敏感词列表（示例，实际应该从数据库或配置文件加载）
    SENSITIVE_WORDS = [
        "政治敏感词示例",
        "暴力词汇示例",
        # ... 更多敏感词
    ]

    # 密码/邮箱/手机号等PII数据正则
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(1[3-9]\d{9})\b',
        'id_card': r'\b[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]\b',
        'password': r'(password|passwd|pwd)[\s:=]+[^\s]+',
    }

    # SQL注入/ XSS检测模式
    INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"(\bor\b|\band\b).*?=",
        r"(script|onerror|onload)=.*?>",
        r"<script.*?>.*?</script>",
    ]

    @classmethod
    def contains_sensitive_words(cls, text: str) -> bool:
        """检测是否包含敏感词"""
        text_lower = text.lower()
        for word in cls.SENSITIVE_WORDS:
            if word.lower() in text_lower:
                return True
        return False

    @classmethod
    def detect_pii_data(cls, text: str) -> List[dict]:
        """
        检测PII（个人身份信息）数据

        Returns:
            List of {"type": str, "match": str, "start": int, "end": int}
        """
        results = []

        for pii_type, pattern in cls.PII_PATTERNS.items():
            for match in re.finditer(pattern, text):
                results.append({
                    "type": pii_type,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })

        return results

    @classmethod
    def mask_pii_data(cls, text: str) -> str:
        """
        脱敏处理PII数据

        Returns:
            脱敏后的文本
        """
        pii_list = cls.detect_pii_data(text)

        # 从后往前替换，避免索引变化
        for pii in sorted(pii_list, key=lambda x: x["start"], reverse=True):
            match = pii["match"]
            pii_type = pii["type"]

            if pii_type == "email":
                # 邮箱脱敏：user***@domain.com
                parts = match.split("@")
                masked = parts[0][:2] + "***@" + parts[1]
                text = text[:pii["start"]] + masked + text[pii["end"]:]

            elif pii_type == "phone":
                # 手机号脱敏：138****5678
                masked = match[:3] + "****" + match[-4:]
                text = text[:pii["start"]] + masked + text[pii["end"]:]

            elif pii_type == "id_card":
                # 身份证脱敏：前6位+8位星号+后4位
                masked = match[:6] + "********" + match[-4:]
                text = text[:pii["start"]] + masked + text[pii["end"]:]

            elif pii_type == "password":
                # 密码完全脱敏
                text = text[:pii["start"]] + "***" + text[pii["end"]:]

        return text

    @classmethod
    def detect_injection(cls, text: str) -> bool:
        """检测SQL注入/XSS攻击"""
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_content(cls, text: str) -> dict:
        """
        内容安全检查和清洗

        Returns:
            {
                "safe": bool,
                "cleaned": str,
                "issues": List[str],
                "pii_found": List[dict]
            }
        """
        issues = []
        cleaned_text = text

        # 1. 检测敏感词
        if cls.contains_sensitive_words(text):
            issues.append("contains_sensitive_words")
            # 不删除敏感词，只标记

        # 2. 检测注入攻击
        if cls.detect_injection(text):
            issues.append("potential_injection")
            # 移除潜在的注入代码
            cleaned_text = re.sub(r'<[^>]*>', '', cleaned_text)

        # 3. 检测PII数据
        pii_found = cls.detect_pii_data(text)
        if pii_found:
            issues.append("contains_pii_data")
            # 脱敏处理
            cleaned_text = cls.mask_pii_data(cleaned_text)

        return {
            "safe": len(issues) == 0,
            "cleaned": cleaned_text,
            "issues": issues,
            "pii_found": pii_found
        }


def filter_user_input(text: str) -> str:
    """过滤用户输入（简化版）"""
    result = ContentFilter.sanitize_content(text)

    if not result["safe"]:
        # 记录安全问题
        if "potential_injection" in result["issues"]:
            print(f"⚠️  检测到潜在注入攻击: {text[:100]}")

        if "contains_sensitive_words" in result["issues"]:
            print(f"⚠️  检测到敏感词: {text[:100]}")

    return result["cleaned"]


def filter_llm_output(text: str) -> str:
    """过滤LLM输出（脱敏PII数据）"""
    result = ContentFilter.sanitize_content(text)

    if result["pii_found"]:
        print(f"ℹ️  LLM输出包含PII数据，已脱敏: {len(result['pii_found'])}处")

    return result["cleaned"]
