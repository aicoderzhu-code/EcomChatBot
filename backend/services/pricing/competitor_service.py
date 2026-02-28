"""竞品数据管理服务"""
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.pricing import CompetitorProduct


class CompetitorService:
    """竞品数据管理服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def add_competitor(
        self,
        product_id: int,
        competitor_name: str,
        competitor_price: float,
        competitor_platform: str | None = None,
        competitor_url: str | None = None,
        competitor_sales: int = 0,
    ) -> CompetitorProduct:
        """添加竞品数据"""
        comp = CompetitorProduct(
            tenant_id=self.tenant_id,
            product_id=product_id,
            competitor_name=competitor_name,
            competitor_price=competitor_price,
            competitor_platform=competitor_platform,
            competitor_url=competitor_url,
            competitor_sales=competitor_sales,
        )
        self.db.add(comp)
        await self.db.commit()
        await self.db.refresh(comp)
        return comp

    async def list_competitors(
        self,
        product_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CompetitorProduct], int]:
        """列出竞品数据"""
        conditions = [
            CompetitorProduct.tenant_id == self.tenant_id,
            CompetitorProduct.product_id == product_id,
        ]
        count_stmt = select(func.count(CompetitorProduct.id)).where(
            and_(*conditions)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(CompetitorProduct)
            .where(and_(*conditions))
            .order_by(CompetitorProduct.competitor_price.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def delete_competitor(self, competitor_id: int) -> bool:
        """删除竞品数据"""
        stmt = select(CompetitorProduct).where(
            and_(
                CompetitorProduct.id == competitor_id,
                CompetitorProduct.tenant_id == self.tenant_id,
            )
        )
        comp = (await self.db.execute(stmt)).scalar_one_or_none()
        if not comp:
            return False
        await self.db.delete(comp)
        await self.db.commit()
        return True
