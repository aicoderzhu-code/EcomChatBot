"""
敏感词过滤服务 - 使用AC自动机
"""
import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import ahocorasick
except ImportError:
    ahocorasick = None
    logging.warning("pyahocorasick not installed, falling back to simple matching")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sensitive_word import SensitiveWord


class FilterLevel(Enum):
    """过滤级别"""

    BLOCK = "block"  # 完全阻止
    REPLACE = "replace"  # 替换为***
    WARNING = "warning"  # 仅警告记录


@dataclass
class FilterResult:
    """过滤结果"""

    is_safe: bool
    filtered_text: str
    detected_words: List[str]
    filter_level: Optional[FilterLevel] = None
    message: Optional[str] = None


class SensitiveWordFilter:
    """敏感词过滤器 - 使用AC自动机"""

    def __init__(self):
        self.automaton = None
        if ahocorasick:
            self.automaton = ahocorasick.Automaton()
        self.word_levels: dict[str, FilterLevel] = {}
        self.word_list: List[str] = []  # 简单匹配的备份方案
        self._initialized = False

    async def load_words(self, db: AsyncSession):
        """从数据库加载敏感词"""
        result = await db.execute(
            select(SensitiveWord).where(SensitiveWord.is_active == True)
        )
        words = result.scalars().all()

        for word in words:
            self.add_word(word.word, FilterLevel(word.level))

        self._build_automaton()

    def add_word(self, word: str, level: FilterLevel = FilterLevel.REPLACE):
        """添加敏感词"""
        word_lower = word.lower()

        if self.automaton:
            self.automaton.add_word(word_lower, word_lower)

        self.word_list.append(word_lower)
        self.word_levels[word_lower] = level

    def _build_automaton(self):
        """构建AC自动机"""
        if self.automaton:
            self.automaton.make_automaton()
        self._initialized = True

    def filter(self, text: str) -> FilterResult:
        """
        过滤文本

        使用AC自动机进行多模式匹配
        """
        if not self._initialized:
            return FilterResult(
                is_safe=True, filtered_text=text, detected_words=[]
            )

        text_lower = text.lower()
        detected_words = []
        highest_level = None

        # 使用AC自动机匹配
        if self.automaton:
            for end_index, word in self.automaton.iter(text_lower):
                if word not in detected_words:
                    detected_words.append(word)
                level = self.word_levels.get(word, FilterLevel.REPLACE)

                if highest_level is None or self._compare_levels(level, highest_level) > 0:
                    highest_level = level
        else:
            # 备份方案：简单匹配
            for word in self.word_list:
                if word in text_lower:
                    detected_words.append(word)
                    level = self.word_levels.get(word, FilterLevel.REPLACE)
                    if highest_level is None or self._compare_levels(level, highest_level) > 0:
                        highest_level = level

        if not detected_words:
            return FilterResult(
                is_safe=True, filtered_text=text, detected_words=[]
            )

        # 根据最高级别处理
        if highest_level == FilterLevel.BLOCK:
            return FilterResult(
                is_safe=False,
                filtered_text="",
                detected_words=detected_words,
                filter_level=FilterLevel.BLOCK,
                message="内容包含违禁词,已被阻止",
            )
        elif highest_level == FilterLevel.REPLACE:
            filtered_text = self._replace_words(text, detected_words)
            return FilterResult(
                is_safe=True,
                filtered_text=filtered_text,
                detected_words=detected_words,
                filter_level=FilterLevel.REPLACE,
            )
        else:  # WARNING
            return FilterResult(
                is_safe=True,
                filtered_text=text,
                detected_words=detected_words,
                filter_level=FilterLevel.WARNING,
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
        enable_contact_filter: bool = True,
    ):
        self.sensitive_filter = sensitive_filter
        self.enable_url_filter = enable_url_filter
        self.enable_contact_filter = enable_contact_filter

    def filter(self, text: str) -> FilterResult:
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
            filter_level=result.filter_level,
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
        phone_pattern = r"1[3-9]\d{9}"
        contacts.extend(re.findall(phone_pattern, text))

        # 邮箱
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        contacts.extend(re.findall(email_pattern, text))

        # 微信号(简单匹配)
        wechat_pattern = r"微信[号:]?\s*([a-zA-Z0-9_-]{6,20})"
        contacts.extend(re.findall(wechat_pattern, text))

        return contacts


# 全局过滤器实例（懒加载）
_global_filter: Optional[ContentFilter] = None


async def init_content_filter(db: AsyncSession):
    """初始化全局内容过滤器"""
    global _global_filter

    sensitive_filter = SensitiveWordFilter()
    await sensitive_filter.load_words(db)

    _global_filter = ContentFilter(sensitive_filter)


def get_content_filter() -> Optional[ContentFilter]:
    """获取全局内容过滤器"""
    return _global_filter


async def filter_text(text: str) -> FilterResult:
    """过滤文本（使用全局过滤器）"""
    if _global_filter:
        return _global_filter.filter(text)

    # 未初始化时，返回安全结果
    return FilterResult(is_safe=True, filtered_text=text, detected_words=[])
