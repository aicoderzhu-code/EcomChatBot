"""外呼内容生成服务"""
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class OutreachContentService:
    """统一的触达内容生成服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def generate_content(
        self,
        user: dict,
        strategy: str,
        template: str | None = None,
        ai_prompt: str | None = None,
        related_products: list[dict] | None = None,
        context: dict | None = None,
    ) -> str:
        """生成触达内容

        Args:
            user: 用户信息 dict (nickname, vip_level, etc.)
            strategy: 内容策略 (template/ai_generated)
            template: 消息模板
            ai_prompt: AI 生成提示词
            related_products: 关联商品列表
            context: 额外上下文 (跟进序号、原因等)
        """
        if strategy == "template" and template:
            return self._render_template(template, user, related_products)
        elif strategy == "ai_generated" and ai_prompt:
            return await self._ai_generate(user, ai_prompt, related_products, context)
        else:
            # 默认生成简单问候
            nickname = user.get("nickname", "客户")
            return f"您好{nickname}，感谢您的关注！有任何需要可以随时联系我们。"

    def _render_template(
        self,
        template: str,
        user: dict,
        products: list[dict] | None = None,
    ) -> str:
        """模板变量替换"""
        variables = {
            "nickname": user.get("nickname", "客户"),
            "vip_level": str(user.get("vip_level", 0)),
        }
        if products:
            first_product = products[0]
            variables["product_name"] = first_product.get("title", "")
            variables["product_price"] = str(first_product.get("price", ""))
            # 多商品列表
            product_names = "、".join(p.get("title", "") for p in products[:3])
            variables["product_list"] = product_names

        # 替换 {variable_name}
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    async def _ai_generate(
        self,
        user: dict,
        prompt: str,
        products: list[dict] | None = None,
        context: dict | None = None,
    ) -> str:
        """通过 LLM 生成个性化消息"""
        try:
            from services.llm_service import LLMService

            # 构建完整的 system prompt
            system_parts = [
                "你是一个专业的电商客服，需要生成一条简短友好的主动触达消息。",
                "要求：1) 语气亲切自然 2) 不要太长(50-100字) 3) 包含明确的价值点",
            ]

            user_info = f"客户昵称: {user.get('nickname', '客户')}, VIP等级: {user.get('vip_level', 0)}"

            if products:
                product_info = "\n".join(
                    f"- {p.get('title', '')} (¥{p.get('price', '')})" for p in products[:3]
                )
                system_parts.append(f"相关商品:\n{product_info}")

            if context:
                if "follow_up_sequence" in context:
                    seq = context["follow_up_sequence"]
                    if seq == 1:
                        system_parts.append("这是第一次跟进，重点关心使用体验。")
                    elif seq == 2:
                        system_parts.append("这是第二次跟进，可以推荐新品或优惠信息。")
                    else:
                        system_parts.append("这是多次跟进，提供专属福利并制造紧迫感。")
                if "reason" in context:
                    system_parts.append(f"跟进原因: {context['reason']}")

            full_prompt = "\n".join(system_parts) + f"\n\n{user_info}\n\n用户指令: {prompt}"

            llm_service = LLMService(self.tenant_id)
            response = await llm_service.generate_response(
                system_prompt=full_prompt,
                user_message="请生成触达消息",
            )
            return response.strip()

        except Exception as e:
            logger.warning(f"AI内容生成失败，使用默认模板: {e}")
            nickname = user.get("nickname", "客户")
            return f"您好{nickname}，感谢您的支持！我们有新品上线，欢迎前来选购。"
