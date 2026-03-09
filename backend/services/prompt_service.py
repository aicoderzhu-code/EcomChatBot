"""
Prompt 模板管理服务
"""
from datetime import datetime
from typing import Any

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts.chat import SystemMessagePromptTemplate


class PromptService:
    """Prompt 模板管理服务"""

    @staticmethod
    def get_system_prompt(
        platform_name: str = "电商平台",
        user_info: dict[str, Any] | None = None,
        tenant_custom_instructions: str | None = None,
    ) -> str:
        """
        获取系统提示词
        
        Args:
            platform_name: 平台名称
            user_info: 用户信息
            tenant_custom_instructions: 租户自定义指令
            
        Returns:
            系统提示词
        """
        user_info = user_info or {}

        base_prompt = f"""你是 {platform_name} 的智能客服助手。

## 角色定位
- 你代表 {platform_name}，提供专业、礼貌、有耐心的客户服务
- 你的主要职责是帮助客户解决问题，提供准确的信息
- 对于不确定的信息，不要编造，诚实告知并提供替代方案

## 能力范围
你可以帮助客户：
1. 商品咨询：商品详情、规格、价格、库存、使用方法等
2. 订单查询：订单状态、物流信息、配送进度
3. 售后服务：退换货政策、申请流程、退款进度
4. 促销活动：优惠券、满减活动、会员权益
5. 支付问题：支付方式、支付失败处理、发票开具
6. 平台规则：注册流程、积分规则、会员体系

## 回答原则
1. 准确性：基于知识库提供准确信息，不确定的信息要说明
2. 简洁性：回答简洁明了，避免冗长
3. 礼貌性：始终保持礼貌和耐心
4. 主动性：主动询问更多细节，以便更好地帮助客户

## 特殊情况处理
- 用户情绪激动：保持冷静，表示理解，提出解决方案
- 投诉问题：认真倾听，记录问题，承诺跟进
- 复杂问题：耐心引导，分步解决
- 敏感信息：不询问密码等敏感信息
"""

        # 添加用户信息
        if user_info:
            user_section = "\n## 当前用户信息\n"
            if user_info.get("user_id"):
                user_section += f"- 用户ID：{user_info['user_id']}\n"
            if user_info.get("vip_level"):
                user_section += f"- VIP等级：{user_info['vip_level']}\n"
            if user_info.get("order_count"):
                user_section += f"- 历史订单数：{user_info['order_count']}\n"

            base_prompt += user_section

        # 添加租户自定义指令
        if tenant_custom_instructions:
            base_prompt += f"\n## 特殊说明\n{tenant_custom_instructions}\n"

        # 添加当前时间
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        base_prompt += f"\n## 当前时间\n{current_time}\n"

        return base_prompt

    @staticmethod
    def get_rag_prompt_template() -> ChatPromptTemplate:
        """
        获取 RAG（检索增强生成）提示词模板
        
        Returns:
            ChatPromptTemplate 实例
        """
        system_template = """你是一个智能客服助手。请基于以下知识库内容回答用户的问题。

## 知识库内容
{context}

## 回答要求
1. 优先使用知识库中的信息回答
2. 如果知识库中没有相关信息，诚实告知用户
3. 回答要简洁、准确、有针对性
4. 如果需要更多信息才能回答，主动询问用户

请根据用户的问题和上述知识库内容，给出专业的回答。
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_template),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{question}"),
            ]
        )

        return prompt

    @staticmethod
    def get_intent_classification_prompt() -> str:
        """
        获取意图分类提示词
        
        Returns:
            意图分类提示词
        """
        return """请分析用户的问题，判断用户的意图类别。

意图类别：
1. ORDER_QUERY: 订单查询（查询订单状态、物流信息等）
2. PRODUCT_INQUIRY: 商品咨询（商品详情、价格、库存等）
3. AFTER_SALES: 售后服务（退换货、退款等）
4. PAYMENT_ISSUE: 支付问题（支付方式、支付失败等）
5. LOGISTICS: 物流查询（配送进度、快递信息等）
6. COMPLAINT: 投诉建议（服务投诉、意见建议等）
7. PROMOTION: 促销咨询（优惠活动、优惠券等）
8. ACCOUNT: 账户问题（注册、登录、会员等）
9. LOGISTICS_QUERY: 查物流（快递到哪了、物流进度查询等）
10. RETURN_EXCHANGE: 退换货（退货申请、换货流程等）
11. URGE_SHIPPING: 催发货（什么时候发货、催促发货等）
12. CHANGE_ADDRESS: 改地址（修改收货地址、更换地址等）
13. COUPON_INQUIRY: 优惠咨询（优惠券使用、满减规则等）
14. PRODUCT_CONSULT: 商品咨询（商品详情、功能介绍等）
15. PRICE_INQUIRY: 价格咨询（商品价格、比价、降价等）
16. SIZE_GUIDE: 尺码指南（尺码推荐、尺码表等）
17. OTHER: 其他

请只返回意图类别名称，不要包含其他内容。

用户问题：{question}

意图类别："""

    @staticmethod
    def get_entity_extraction_prompt() -> str:
        """
        获取实体提取提示词
        
        Returns:
            实体提取提示词
        """
        return """请从用户的问题中提取关键实体信息。

需要提取的实体类型：
1. order_number: 订单号
2. product_name: 商品名称
3. product_id: 商品ID
4. amount: 金额
5. date: 日期
6. phone: 手机号
7. address: 地址

请以 JSON 格式返回提取的实体，如果没有对应实体则省略。

用户问题：{question}

提取的实体（JSON格式）："""

    @staticmethod
    def get_summary_generation_prompt() -> str:
        """获取摘要生成提示词"""
        return """请对以下客服对话生成一段简洁的摘要。

## 要求
1. 概述用户的主要问题或需求
2. 说明客服提供的解决方案或回答
3. 记录最终结论或处理结果
4. 如果有未解决的问题也要提及
5. 摘要控制在 100-200 字以内

## 对话内容
{conversation}

## 摘要："""

    @staticmethod
    def format_conversation_history(
        messages: list[dict[str, str]],
        max_messages: int = 10,
    ) -> str:
        """
        格式化对话历史
        
        Args:
            messages: 消息列表
            max_messages: 最大消息数量
            
        Returns:
            格式化后的对话历史
        """
        # 只取最近的 N 条消息
        recent_messages = messages[-max_messages:] if messages else []

        formatted = []
        for msg in recent_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                formatted.append(f"用户：{content}")
            elif role == "assistant":
                formatted.append(f"助手：{content}")

        return "\n".join(formatted)

    @staticmethod
    def build_context_from_knowledge(
        knowledge_items: list[dict[str, Any]],
        max_items: int = 5,
    ) -> str:
        """
        从知识库项构建上下文
        
        Args:
            knowledge_items: 知识库项列表
            max_items: 最大项数
            
        Returns:
            构建的上下文字符串
        """
        context_parts = []

        for idx, item in enumerate(knowledge_items[:max_items], 1):
            title = item.get("title", "")
            content = item.get("content", "")
            source = item.get("source", "")

            part = f"[知识{idx}]"
            if title:
                part += f" {title}\n"
            part += f"{content}"
            if source:
                part += f"\n（来源：{source}）"

            context_parts.append(part)

        return "\n\n".join(context_parts)
