"""定价分析服务"""
import logging

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.pricing import CompetitorProduct, PricingAnalysis
from models.product import Product

logger = logging.getLogger(__name__)


class PricingService:
    """定价分析服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def analyze_pricing(
        self, product_id: int, strategy: str = "competitive"
    ) -> PricingAnalysis:
        """分析商品定价"""
        # 获取商品
        product = (
            await self.db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not product:
            raise ValueError("商品不存在")

        # 获取竞品数据
        competitors = (
            await self.db.execute(
                select(CompetitorProduct).where(
                    and_(
                        CompetitorProduct.product_id == product_id,
                        CompetitorProduct.tenant_id == self.tenant_id,
                    )
                )
            )
        ).scalars().all()

        competitor_prices = [float(c.competitor_price) for c in competitors]
        competitor_count = len(competitor_prices)
        avg_price = (
            sum(competitor_prices) / len(competitor_prices)
            if competitor_prices
            else None
        )

        # 计算建议价格
        suggested_price, min_price, max_price = self._calculate_price(
            current_price=float(product.price),
            competitor_prices=competitor_prices,
            strategy=strategy,
        )

        # AI 生成分析摘要
        summary = await self._generate_analysis_summary(
            product, competitors, suggested_price, strategy
        )

        # 保存分析结果
        analysis = PricingAnalysis(
            tenant_id=self.tenant_id,
            product_id=product_id,
            current_price=float(product.price),
            suggested_price=suggested_price,
            min_price=min_price,
            max_price=max_price,
            strategy=strategy,
            competitor_count=competitor_count,
            competitor_avg_price=avg_price,
            analysis_summary=summary,
            analysis_data={
                "competitor_prices": competitor_prices,
                "product_sales": product.sales_count,
                "product_stock": product.stock,
            },
        )
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    def _calculate_price(
        self,
        current_price: float,
        competitor_prices: list[float],
        strategy: str,
    ) -> tuple[float, float, float]:
        """根据策略计算建议价格"""
        if not competitor_prices:
            return current_price, current_price * 0.8, current_price * 1.2

        avg = sum(competitor_prices) / len(competitor_prices)
        min_comp = min(competitor_prices)
        max_comp = max(competitor_prices)

        if strategy == "competitive":
            suggested = round(avg * 0.95, 2)
        elif strategy == "premium":
            suggested = round(avg * 1.15, 2)
        elif strategy == "penetration":
            suggested = round(min_comp * 0.9, 2)
        else:  # dynamic
            suggested = round(avg, 2)

        return suggested, round(min_comp * 0.85, 2), round(max_comp * 1.1, 2)

    async def _generate_analysis_summary(
        self, product, competitors, suggested_price, strategy
    ) -> str | None:
        """AI 生成分析摘要"""
        try:
            from services.llm_service import LLMService

            comp_info = ", ".join(
                [
                    f"{c.competitor_name}(¥{c.competitor_price})"
                    for c in competitors[:5]
                ]
            )
            prompt = f"""分析以下商品定价情况并给出建议：
商品：{product.title}，当前价格：¥{product.price}，销量：{product.sales_count}
竞品：{comp_info or '暂无竞品数据'}
定价策略：{strategy}，建议价格：¥{suggested_price}
请用2-3句话总结分析结果。"""
            llm_service = LLMService(tenant_id=self.tenant_id)
            return await llm_service.generate_response(
                messages=[{"role": "user", "content": prompt}]
            )
        except Exception as e:
            logger.warning("生成定价分析摘要失败: %s", e)
            return None

    async def get_latest_analysis(
        self, product_id: int
    ) -> PricingAnalysis | None:
        """获取最新分析结果"""
        stmt = (
            select(PricingAnalysis)
            .where(
                and_(
                    PricingAnalysis.product_id == product_id,
                    PricingAnalysis.tenant_id == self.tenant_id,
                )
            )
            .order_by(PricingAnalysis.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_analyses(
        self, product_id: int, page: int = 1, size: int = 10
    ) -> tuple[list[PricingAnalysis], int]:
        """列出分析历史"""
        conditions = [
            PricingAnalysis.product_id == product_id,
            PricingAnalysis.tenant_id == self.tenant_id,
        ]
        count_stmt = select(func.count(PricingAnalysis.id)).where(
            and_(*conditions)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(PricingAnalysis)
            .where(and_(*conditions))
            .order_by(PricingAnalysis.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
