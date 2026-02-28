"""文案生成服务 - 标题/描述生成"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.product import Product

logger = logging.getLogger(__name__)


class CopywritingService:
    """商品文案（标题/描述）生成服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def generate_titles(
        self, product_id: int, count: int = 5, style: str = "电商"
    ) -> list[str]:
        """生成商品标题"""
        product = await self._get_product(product_id)
        if not product:
            raise ValueError("商品不存在")

        prompt = f"""请为以下商品生成{count}个电商标题：
商品名称：{product.title}
商品分类：{product.category or '未分类'}
商品价格：{product.price}元
商品描述：{product.description or '无'}
风格：{style}

请生成{count}个不同角度的标题，每行一个，不要编号。"""

        from services.llm_service import LLMService

        llm_service = LLMService(tenant_id=self.tenant_id)
        result = await llm_service.generate_response(
            messages=[{"role": "user", "content": prompt}]
        )
        titles = [line.strip() for line in result.strip().split("\n") if line.strip()]
        return titles[:count]

    async def generate_description(
        self, product_id: int, style: str = "详细"
    ) -> str:
        """生成商品描述"""
        product = await self._get_product(product_id)
        if not product:
            raise ValueError("商品不存在")

        prompt = f"""请为以下商品生成一段电商描述文案：
商品名称：{product.title}
商品分类：{product.category or '未分类'}
商品价格：{product.price}元
当前描述：{product.description or '无'}
规格属性：{product.attributes or '无'}
风格：{style}

请生成一段吸引买家的商品描述，突出卖点和特色。"""

        from services.llm_service import LLMService

        llm_service = LLMService(tenant_id=self.tenant_id)
        result = await llm_service.generate_response(
            messages=[{"role": "user", "content": prompt}]
        )
        return result.strip()

    async def _get_product(self, product_id: int) -> Product | None:
        """获取商品"""
        stmt = select(Product).where(
            Product.id == product_id, Product.tenant_id == self.tenant_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
