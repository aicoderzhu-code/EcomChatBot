"""推荐引擎 — 对话实时推荐 + 购买后推荐"""
import logging
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order
from models.product import Product
from models.recommendation import RecommendationLog, RecommendationRule
from models.outreach import OutreachTask

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def get_in_conversation_recommendations(
        self,
        user_id: int,
        conversation_context: str | None = None,
        current_product_id: int | None = None,
    ) -> dict | None:
        """对话中实时推荐"""
        rules = await self._get_active_rules("in_conversation")
        if not rules:
            return None

        for rule in rules:
            # 检查是否匹配触发条件
            if current_product_id and rule.trigger_product_ids:
                if current_product_id not in rule.trigger_product_ids:
                    continue

            # 获取候选商品
            products = await self._get_candidate_products(rule, current_product_id)
            if not products:
                continue

            # 生成推荐文案
            text = await self._generate_recommendation_text(rule, products)

            # 记录日志
            product_ids = [p.id for p in products]
            log = RecommendationLog(
                tenant_id=self.tenant_id,
                user_id=user_id,
                rule_id=rule.id,
                trigger_type="in_conversation",
                trigger_product_id=current_product_id,
                recommended_product_ids=product_ids,
                recommendation_text=text,
                displayed=1,
            )
            self.db.add(log)
            await self.db.flush()

            return {
                "rule_id": rule.id,
                "products": [
                    {"id": p.id, "title": p.title, "price": float(p.price), "images": p.images}
                    for p in products
                ],
                "text": text,
                "log_id": log.id,
            }

        return None

    async def get_post_purchase_recommendations(
        self,
        user_id: int,
        order_id: int,
    ) -> dict | None:
        """购买后推荐"""
        # 获取订单商品
        order_stmt = select(Order).where(
            and_(Order.id == order_id, Order.tenant_id == self.tenant_id)
        )
        order = (await self.db.execute(order_stmt)).scalar_one_or_none()
        if not order:
            return None

        trigger_product_id = order.product_id
        rules = await self._get_active_rules("post_purchase")

        for rule in rules:
            if trigger_product_id and rule.trigger_product_ids:
                if trigger_product_id not in rule.trigger_product_ids:
                    continue

            # 按分类匹配
            if rule.trigger_category and trigger_product_id:
                prod = (await self.db.execute(
                    select(Product).where(Product.id == trigger_product_id)
                )).scalar_one_or_none()
                if prod and prod.category != rule.trigger_category:
                    continue

            products = await self._get_candidate_products(rule, trigger_product_id)
            if not products:
                continue

            text = await self._generate_recommendation_text(rule, products)
            product_ids = [p.id for p in products]

            # 记录日志
            log = RecommendationLog(
                tenant_id=self.tenant_id,
                user_id=user_id,
                rule_id=rule.id,
                trigger_type="post_purchase",
                trigger_product_id=trigger_product_id,
                trigger_order_id=order_id,
                recommended_product_ids=product_ids,
                recommendation_text=text,
                displayed=0,
            )
            self.db.add(log)

            # 创建触达任务
            task = OutreachTask(
                tenant_id=self.tenant_id,
                user_id=user_id,
                related_product_ids=product_ids,
                related_order_id=order_id,
                content=text,
                content_generated_at=datetime.utcnow(),
                status="pending",
                scheduled_at=datetime.utcnow(),
            )
            self.db.add(task)
            await self.db.flush()

            # 异步投递
            from tasks.outreach_tasks import deliver_outreach_task
            deliver_outreach_task.delay(task.id, self.tenant_id)

            return {
                "rule_id": rule.id,
                "products": [
                    {"id": p.id, "title": p.title, "price": float(p.price)}
                    for p in products
                ],
                "text": text,
            }

        return None

    async def _get_active_rules(self, trigger_type: str) -> list[RecommendationRule]:
        stmt = (
            select(RecommendationRule)
            .where(
                and_(
                    RecommendationRule.tenant_id == self.tenant_id,
                    RecommendationRule.is_active == 1,
                    RecommendationRule.trigger_type == trigger_type,
                )
            )
            .order_by(RecommendationRule.priority.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_candidate_products(
        self,
        rule: RecommendationRule,
        trigger_product_id: int | None = None,
    ) -> list[Product]:
        """获取候选推荐商品"""
        limit = rule.max_recommendations

        if rule.recommend_strategy == "manual" and rule.recommend_product_ids:
            stmt = select(Product).where(
                and_(
                    Product.id.in_(rule.recommend_product_ids),
                    Product.status == "active",
                )
            ).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        if rule.recommend_strategy == "popular_in_category":
            category = rule.recommend_category
            if not category and trigger_product_id:
                prod = (await self.db.execute(
                    select(Product).where(Product.id == trigger_product_id)
                )).scalar_one_or_none()
                if prod:
                    category = prod.category

            if category:
                stmt = (
                    select(Product)
                    .where(
                        and_(
                            Product.tenant_id == self.tenant_id,
                            Product.category == category,
                            Product.status == "active",
                        )
                    )
                    .order_by(Product.sales_count.desc())
                    .limit(limit)
                )
                # 排除触发商品
                if trigger_product_id:
                    stmt = stmt.where(Product.id != trigger_product_id)
                result = await self.db.execute(stmt)
                return list(result.scalars().all())

        if rule.recommend_strategy in ("ai_similar", "ai_complementary") and trigger_product_id:
            # 尝试向量搜索
            try:
                return await self._vector_search_products(trigger_product_id, limit)
            except Exception as e:
                logger.warning(f"向量搜索失败，回退到分类推荐: {e}")
                # 回退到同分类热门
                prod = (await self.db.execute(
                    select(Product).where(Product.id == trigger_product_id)
                )).scalar_one_or_none()
                if prod and prod.category:
                    stmt = (
                        select(Product)
                        .where(
                            and_(
                                Product.tenant_id == self.tenant_id,
                                Product.category == prod.category,
                                Product.status == "active",
                                Product.id != trigger_product_id,
                            )
                        )
                        .order_by(Product.sales_count.desc())
                        .limit(limit)
                    )
                    result = await self.db.execute(stmt)
                    return list(result.scalars().all())

        return []

    async def _vector_search_products(self, product_id: int, limit: int) -> list[Product]:
        """通过向量相似度搜索相关商品"""
        from services.embedding_service import EmbeddingService
        from services.milvus_service import MilvusService

        product = (await self.db.execute(
            select(Product).where(Product.id == product_id)
        )).scalar_one_or_none()
        if not product:
            return []

        # 生成嵌入
        embedding_service = EmbeddingService(self.tenant_id)
        text = f"{product.title} {product.description or ''}"
        vector = await embedding_service.embed_text(text)

        # 搜索相似
        milvus_service = MilvusService()
        results = await milvus_service.search(
            collection_name=f"products_{self.tenant_id}",
            query_vector=vector,
            top_k=limit + 1,  # +1 排除自身
        )

        # 获取商品
        product_ids = [r["id"] for r in results if r["id"] != product_id][:limit]
        if not product_ids:
            return []

        stmt = select(Product).where(
            and_(Product.id.in_(product_ids), Product.status == "active")
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _generate_recommendation_text(
        self,
        rule: RecommendationRule,
        products: list[Product],
    ) -> str:
        """生成推荐文案"""
        product_names = "、".join(p.title for p in products[:3])

        if rule.ai_prompt:
            try:
                from services.llm_service import LLMService
                llm = LLMService(self.tenant_id)
                product_info = "\n".join(
                    f"- {p.title} (¥{p.price})" for p in products[:3]
                )
                prompt = f"{rule.ai_prompt}\n\n推荐商品:\n{product_info}"
                text = await llm.generate_response(
                    system_prompt="你是电商客服，生成简短的商品推荐文案(30-60字)，语气亲切。",
                    user_message=prompt,
                )
                return text.strip()
            except Exception as e:
                logger.warning(f"AI推荐文案生成失败: {e}")

        # 默认文案
        type_labels = {
            "cross_sell": "搭配推荐",
            "upsell": "升级推荐",
            "accessory": "配件推荐",
            "consumable": "耗材补充",
            "replenish": "复购提醒",
        }
        label = type_labels.get(rule.rule_type, "为您推荐")
        return f"【{label}】您可能还需要: {product_names}，欢迎选购！"
