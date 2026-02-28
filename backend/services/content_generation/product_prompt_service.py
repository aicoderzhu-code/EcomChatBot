"""商品提示词管理服务"""
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.product_prompt import ProductPrompt


class ProductPromptService:
    """商品提示词 CRUD"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_prompt(
        self, product_id: int, prompt_type: str, name: str, content: str,
    ) -> ProductPrompt:
        prompt = ProductPrompt(
            tenant_id=self.tenant_id,
            product_id=product_id,
            prompt_type=prompt_type,
            name=name,
            content=content,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def get_prompt(self, prompt_id: int) -> ProductPrompt | None:
        stmt = select(ProductPrompt).where(
            and_(ProductPrompt.id == prompt_id, ProductPrompt.tenant_id == self.tenant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_prompts(
        self,
        product_id: int | None = None,
        prompt_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ProductPrompt], int]:
        conditions = [ProductPrompt.tenant_id == self.tenant_id]
        if product_id:
            conditions.append(ProductPrompt.product_id == product_id)
        if prompt_type:
            conditions.append(ProductPrompt.prompt_type == prompt_type)

        total = (await self.db.execute(
            select(func.count(ProductPrompt.id)).where(and_(*conditions))
        )).scalar() or 0

        stmt = (
            select(ProductPrompt)
            .where(and_(*conditions))
            .order_by(ProductPrompt.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def update_prompt(self, prompt_id: int, **kwargs) -> ProductPrompt | None:
        prompt = await self.get_prompt(prompt_id)
        if not prompt:
            return None
        for key, value in kwargs.items():
            if hasattr(prompt, key) and value is not None:
                setattr(prompt, key, value)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def delete_prompt(self, prompt_id: int) -> bool:
        prompt = await self.get_prompt(prompt_id)
        if not prompt:
            return False
        await self.db.delete(prompt)
        await self.db.commit()
        return True

    async def increment_usage(self, prompt_id: int) -> None:
        prompt = await self.get_prompt(prompt_id)
        if prompt:
            prompt.usage_count += 1
            await self.db.commit()
