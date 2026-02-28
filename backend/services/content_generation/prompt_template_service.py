"""提示词模板服务"""
import re

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.prompt_template import PromptTemplate


class PromptTemplateService:
    """提示词模板 CRUD + 变量替换"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create_template(
        self, name: str, template_type: str, content: str,
        variables: list[str] | None = None, is_default: bool = False,
    ) -> PromptTemplate:
        template = PromptTemplate(
            tenant_id=self.tenant_id,
            name=name,
            template_type=template_type,
            content=content,
            variables=variables,
            is_default=1 if is_default else 0,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: int) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(
            and_(
                PromptTemplate.id == template_id,
                PromptTemplate.tenant_id == self.tenant_id,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_templates(
        self, template_type: str | None = None, page: int = 1, size: int = 20
    ) -> tuple[list[PromptTemplate], int]:
        conditions = [PromptTemplate.tenant_id == self.tenant_id]
        if template_type:
            conditions.append(PromptTemplate.template_type == template_type)

        count_stmt = select(func.count(PromptTemplate.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(PromptTemplate)
            .where(and_(*conditions))
            .order_by(PromptTemplate.is_default.desc(), PromptTemplate.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        templates = list(result.scalars().all())
        return templates, total

    async def update_template(
        self, template_id: int,
        name: str | None = None, content: str | None = None,
        variables: list[str] | None = None, is_default: bool | None = None,
    ) -> PromptTemplate | None:
        template = await self.get_template(template_id)
        if not template:
            return None
        if name is not None:
            template.name = name
        if content is not None:
            template.content = content
        if variables is not None:
            template.variables = variables
        if is_default is not None:
            template.is_default = 1 if is_default else 0
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        template = await self.get_template(template_id)
        if not template:
            return False
        await self.db.delete(template)
        await self.db.commit()
        return True

    @staticmethod
    def render_template(content: str, variables: dict[str, str]) -> str:
        """将模板中的变量占位符替换为实际值"""
        result = content
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
