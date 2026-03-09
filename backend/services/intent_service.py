"""
意图识别服务
支持基于规则的快速匹配和基于 LLM 的智能分类
"""
import re
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class IntentType(str, Enum):
    """意图类型枚举"""

    ORDER_QUERY = "ORDER_QUERY"  # 订单查询
    PRODUCT_INQUIRY = "PRODUCT_INQUIRY"  # 商品咨询
    AFTER_SALES = "AFTER_SALES"  # 售后服务
    PAYMENT_ISSUE = "PAYMENT_ISSUE"  # 支付问题
    LOGISTICS = "LOGISTICS"  # 物流查询
    COMPLAINT = "COMPLAINT"  # 投诉建议
    PROMOTION = "PROMOTION"  # 促销咨询
    ACCOUNT = "ACCOUNT"  # 账户问题
    LOGISTICS_QUERY = "LOGISTICS_QUERY"  # 查物流
    RETURN_EXCHANGE = "RETURN_EXCHANGE"  # 退换货
    URGE_SHIPPING = "URGE_SHIPPING"  # 催发货
    CHANGE_ADDRESS = "CHANGE_ADDRESS"  # 改地址
    COUPON_INQUIRY = "COUPON_INQUIRY"  # 优惠咨询
    PRODUCT_CONSULT = "PRODUCT_CONSULT"  # 商品咨询
    PRICE_INQUIRY = "PRICE_INQUIRY"  # 价格咨询
    SIZE_GUIDE = "SIZE_GUIDE"  # 尺码指南
    OTHER = "OTHER"  # 其他


class IntentService:
    """意图识别服务"""

    # 基于规则的关键词匹配
    INTENT_KEYWORDS = {
        IntentType.ORDER_QUERY: [
            "订单",
            "订单号",
            "查订单",
            "订单状态",
            "订单信息",
            "订单查询",
            "我的订单",
            "查询订单",
        ],
        IntentType.PRODUCT_INQUIRY: [
            "商品",
            "产品",
            "多少钱",
            "价格",
            "有货吗",
            "库存",
            "规格",
            "参数",
            "怎么用",
            "介绍一下",
            "详情",
        ],
        IntentType.AFTER_SALES: [
            "退货",
            "退款",
            "换货",
            "售后",
            "退",
            "换",
            "质量问题",
            "坏了",
            "不好用",
            "退换",
        ],
        IntentType.PAYMENT_ISSUE: [
            "支付",
            "付款",
            "支付失败",
            "扣款",
            "没支付成功",
            "付不了",
            "发票",
            "开票",
        ],
        IntentType.LOGISTICS: [
            "物流",
            "快递",
            "配送",
            "发货",
            "什么时候到",
            "到哪了",
            "物流信息",
            "快递单号",
            "没收到",
        ],
        IntentType.COMPLAINT: [
            "投诉",
            "差评",
            "不满意",
            "态度差",
            "太慢了",
            "建议",
            "意见",
        ],
        IntentType.PROMOTION: [
            "优惠",
            "折扣",
            "活动",
            "优惠券",
            "满减",
            "促销",
            "特价",
            "会员",
            "积分",
        ],
        IntentType.ACCOUNT: [
            "注册",
            "登录",
            "账号",
            "密码",
            "忘记密码",
            "找回密码",
            "会员",
            "个人信息",
        ],
        IntentType.LOGISTICS_QUERY: [
            "查物流",
            "快递到哪了",
            "物流进度",
            "物流查询",
            "快递进度",
            "包裹到哪",
            "运单查询",
            "物流跟踪",
        ],
        IntentType.RETURN_EXCHANGE: [
            "退换货",
            "退货申请",
            "换货",
            "退货流程",
            "换货流程",
            "申请退货",
            "申请换货",
            "退换",
            "怎么退货",
        ],
        IntentType.URGE_SHIPPING: [
            "催发货",
            "什么时候发货",
            "催促发货",
            "还没发货",
            "赶紧发货",
            "加急发货",
            "尽快发货",
            "几天发货",
        ],
        IntentType.CHANGE_ADDRESS: [
            "改地址",
            "修改地址",
            "更换地址",
            "修改收货地址",
            "换地址",
            "改收货地址",
            "变更地址",
        ],
        IntentType.COUPON_INQUIRY: [
            "优惠券怎么用",
            "满减规则",
            "优惠咨询",
            "怎么用优惠券",
            "有没有优惠",
            "领券",
            "红包",
            "折扣码",
        ],
        IntentType.PRODUCT_CONSULT: [
            "商品咨询",
            "商品详情",
            "功能介绍",
            "产品介绍",
            "有什么功能",
            "材质",
            "成分",
            "保质期",
        ],
        IntentType.PRICE_INQUIRY: [
            "多少钱",
            "价格多少",
            "什么价格",
            "比价",
            "降价",
            "会不会降价",
            "最低价",
            "价格查询",
        ],
        IntentType.SIZE_GUIDE: [
            "尺码",
            "尺码推荐",
            "尺码表",
            "穿多大",
            "选什么码",
            "大小怎么选",
            "尺寸",
            "偏大还是偏小",
        ],
    }

    # 正则表达式模式
    ORDER_NUMBER_PATTERN = r'\d{10,20}'  # 订单号通常是 10-20 位数字
    PHONE_PATTERN = r'1[3-9]\d{9}'  # 手机号
    AMOUNT_PATTERN = r'(\d+\.?\d*)\s*(元|块|rmb)'  # 金额

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        初始化意图识别服务
        
        Args:
            db: 数据库会话
            tenant_id: 租户 ID
        """
        self.db = db
        self.tenant_id = tenant_id

    def classify_intent_by_rules(self, user_input: str) -> IntentType:
        """
        基于规则快速分类意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            意图类型
        """
        user_input_lower = user_input.lower()

        # 计算每个意图的匹配分数
        scores = {intent: 0 for intent in IntentType}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    scores[intent] += 1

        # 找到最高分的意图
        max_score = max(scores.values())

        if max_score > 0:
            for intent, score in scores.items():
                if score == max_score:
                    return intent

        # 如果没有匹配，返回 OTHER
        return IntentType.OTHER

    async def classify_intent_by_llm(
        self,
        user_input: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> IntentType:
        """
        基于 LLM 智能分类意图
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史（可选，用于上下文）
            
        Returns:
            意图类型
        """
        # 使用 ConversationChainService 进行意图分类
        from services import ConversationChainService

        chain = ConversationChainService(
            db=self.db,
            tenant_id=self.tenant_id,
            conversation_id="intent-classification",  # 临时会话 ID
        )

        intent_str = await chain.classify_intent(user_input)

        # 转换为枚举
        try:
            return IntentType(intent_str)
        except ValueError:
            return IntentType.OTHER

    async def classify_intent_hybrid(
        self,
        user_input: str,
        use_llm_fallback: bool = True,
    ) -> dict[str, Any]:
        """
        混合意图分类（规则 + LLM）
        
        Args:
            user_input: 用户输入
            use_llm_fallback: 当规则匹配不确定时，是否使用 LLM
            
        Returns:
            意图分类结果
        """
        # 1. 先用规则快速匹配
        rule_intent = self.classify_intent_by_rules(user_input)
        confidence = "high" if rule_intent != IntentType.OTHER else "low"

        # 2. 如果规则匹配不确定，且启用 LLM，则使用 LLM
        llm_intent = None
        if use_llm_fallback and rule_intent == IntentType.OTHER:
            try:
                llm_intent = await self.classify_intent_by_llm(user_input)
                confidence = "medium"
            except Exception as e:
                print(f"LLM 意图分类失败: {e}")
                llm_intent = IntentType.OTHER

        # 3. 返回结果
        final_intent = llm_intent if llm_intent else rule_intent

        return {
            "intent": final_intent.value,
            "confidence": confidence,
            "rule_intent": rule_intent.value,
            "llm_intent": llm_intent.value if llm_intent else None,
            "method": "hybrid" if llm_intent else "rule",
        }

    def extract_entities_by_rules(self, user_input: str) -> dict[str, Any]:
        """
        基于规则提取实体
        
        Args:
            user_input: 用户输入
            
        Returns:
            提取的实体字典
        """
        entities = {}

        # 提取订单号
        order_numbers = re.findall(self.ORDER_NUMBER_PATTERN, user_input)
        if order_numbers:
            entities["order_number"] = order_numbers[0]

        # 提取手机号
        phones = re.findall(self.PHONE_PATTERN, user_input)
        if phones:
            entities["phone"] = phones[0]

        # 提取金额
        amounts = re.findall(self.AMOUNT_PATTERN, user_input, re.IGNORECASE)
        if amounts:
            entities["amount"] = float(amounts[0][0])

        # 提取日期（简单匹配）
        date_patterns = [
            r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',  # 2024年1月1日
            r'(\d{1,2})[月\-/](\d{1,2})[日号]',  # 1月1日
        ]

        for pattern in date_patterns:
            dates = re.findall(pattern, user_input)
            if dates:
                entities["date"] = dates[0]
                break

        return entities

    async def extract_entities_hybrid(
        self,
        user_input: str,
        use_llm: bool = True,
    ) -> dict[str, Any]:
        """
        混合实体提取（规则 + LLM）
        
        Args:
            user_input: 用户输入
            use_llm: 是否使用 LLM 增强
            
        Returns:
            提取的实体
        """
        # 1. 规则提取
        rule_entities = self.extract_entities_by_rules(user_input)

        # 2. LLM 提取（可选）
        llm_entities = {}
        if use_llm:
            try:
                from services import ConversationChainService

                chain = ConversationChainService(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    conversation_id="entity-extraction",
                )
                llm_entities = await chain.extract_entities(user_input)
            except Exception as e:
                print(f"LLM 实体提取失败: {e}")

        # 3. 合并结果（LLM 结果优先）
        merged_entities = rule_entities.copy()
        merged_entities.update(llm_entities)

        return {
            "entities": merged_entities,
            "rule_entities": rule_entities,
            "llm_entities": llm_entities,
            "method": "hybrid" if llm_entities else "rule",
        }

    def get_intent_confidence(
        self,
        user_input: str,
        intent: IntentType,
    ) -> float:
        """
        计算意图置信度
        
        Args:
            user_input: 用户输入
            intent: 意图类型
            
        Returns:
            置信度 (0-1)
        """
        user_input_lower = user_input.lower()

        # 计算关键词匹配数
        keywords = self.INTENT_KEYWORDS.get(intent, [])
        matches = sum(1 for kw in keywords if kw in user_input_lower)

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.6
        elif matches == 2:
            return 0.8
        else:
            return 0.95

    def get_available_intents(self, enabled_modules: list[str]) -> list[IntentType]:
        """
        根据租户启用的模块，返回可用的意图类型
        
        Args:
            enabled_modules: 启用的功能模块列表
            
        Returns:
            可用的意图类型列表
        """
        # 模块与意图的映射
        module_intent_mapping = {
            "ORDER_QUERY": [IntentType.ORDER_QUERY],
            "AFTER_SALES": [IntentType.AFTER_SALES],
            "DATA_ANALYTICS": [],  # 数据分析不对应前端意图
        }

        # 基础意图（所有租户都有）
        available_intents = [
            IntentType.PRODUCT_INQUIRY,
            IntentType.PAYMENT_ISSUE,
            IntentType.LOGISTICS,
            IntentType.COMPLAINT,
            IntentType.PROMOTION,
            IntentType.ACCOUNT,
            IntentType.LOGISTICS_QUERY,
            IntentType.RETURN_EXCHANGE,
            IntentType.URGE_SHIPPING,
            IntentType.CHANGE_ADDRESS,
            IntentType.COUPON_INQUIRY,
            IntentType.PRODUCT_CONSULT,
            IntentType.PRICE_INQUIRY,
            IntentType.SIZE_GUIDE,
            IntentType.OTHER,
        ]

        # 添加模块对应的意图
        for module in enabled_modules:
            if module in module_intent_mapping:
                available_intents.extend(module_intent_mapping[module])

        return list(set(available_intents))  # 去重
