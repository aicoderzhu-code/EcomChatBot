"""
敏感词管理接口
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.sensitive_word import SensitiveWord
from api.dependencies import AdminDep
from schemas.base import ApiResponse


router = APIRouter(prefix="/sensitive-words", tags=["敏感词管理"])


# ==================== Schemas ====================


class SensitiveWordCreate(BaseModel):
    """创建敏感词"""

    word: str = Field(..., description="敏感词", max_length=128)
    level: str = Field(..., description="过滤级别: block/replace/warning")
    category: str = Field(..., description="分类", max_length=64)
    remark: Optional[str] = Field(None, description="备注", max_length=255)


class SensitiveWordUpdate(BaseModel):
    """更新敏感词"""

    level: Optional[str] = Field(None, description="过滤级别")
    category: Optional[str] = Field(None, description="分类")
    is_active: Optional[bool] = Field(None, description="是否启用")
    remark: Optional[str] = Field(None, description="备注")


class SensitiveWordResponse(BaseModel):
    """敏感词响应"""

    id: int
    word: str
    level: str
    category: str
    is_active: bool
    created_by: Optional[str]
    remark: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SensitiveWordListResponse(BaseModel):
    """敏感词列表响应"""

    items: List[SensitiveWordResponse]
    total: int
    page: int
    page_size: int


# ==================== 接口 ====================


@router.post("", response_model=ApiResponse[SensitiveWordResponse])
async def create_sensitive_word(
    admin: AdminDep,
    body: SensitiveWordCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建敏感词

    需要管理员权限
    """
    # 检查是否已存在
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.word == body.word)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="敏感词已存在")

    # 创建敏感词
    sensitive_word = SensitiveWord(
        word=body.word,
        level=body.level,
        category=body.category,
        remark=body.remark,
        created_by=admin.username,
    )

    db.add(sensitive_word)
    await db.commit()
    await db.refresh(sensitive_word)

    # 重新加载过滤器
    from services.content_filter_service import init_content_filter

    await init_content_filter(db)

    return ApiResponse(success=True, data=sensitive_word, message="创建成功")


@router.get("", response_model=ApiResponse[SensitiveWordListResponse])
async def list_sensitive_words(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    level: Optional[str] = Query(None, description="级别筛选"),
    is_active: Optional[bool] = Query(None, description="启用状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
):
    """
    获取敏感词列表

    支持分页和筛选
    """
    # 构建查询条件
    conditions = []
    if category:
        conditions.append(SensitiveWord.category == category)
    if level:
        conditions.append(SensitiveWord.level == level)
    if is_active is not None:
        conditions.append(SensitiveWord.is_active == is_active)
    if keyword:
        conditions.append(SensitiveWord.word.contains(keyword))

    # 查询总数
    count_result = await db.execute(
        select(func.count(SensitiveWord.id)).where(*conditions)
    )
    total = count_result.scalar()

    # 查询列表
    result = await db.execute(
        select(SensitiveWord)
        .where(*conditions)
        .order_by(SensitiveWord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return ApiResponse(
        success=True,
        data=SensitiveWordListResponse(
            items=items, total=total, page=page, page_size=page_size
        ),
    )


@router.get("/{word_id}", response_model=ApiResponse[SensitiveWordResponse])
async def get_sensitive_word(
    admin: AdminDep,
    word_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取敏感词详情"""
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    sensitive_word = result.scalar_one_or_none()

    if not sensitive_word:
        raise HTTPException(status_code=404, detail="敏感词不存在")

    return ApiResponse(success=True, data=sensitive_word)


@router.put("/{word_id}", response_model=ApiResponse[SensitiveWordResponse])
async def update_sensitive_word(
    admin: AdminDep,
    word_id: int,
    body: SensitiveWordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新敏感词"""
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    sensitive_word = result.scalar_one_or_none()

    if not sensitive_word:
        raise HTTPException(status_code=404, detail="敏感词不存在")

    # 更新字段
    if body.level is not None:
        sensitive_word.level = body.level
    if body.category is not None:
        sensitive_word.category = body.category
    if body.is_active is not None:
        sensitive_word.is_active = body.is_active
    if body.remark is not None:
        sensitive_word.remark = body.remark

    await db.commit()
    await db.refresh(sensitive_word)

    # 重新加载过滤器
    from services.content_filter_service import init_content_filter

    await init_content_filter(db)

    return ApiResponse(success=True, data=sensitive_word, message="更新成功")


@router.delete("/{word_id}", response_model=ApiResponse)
async def delete_sensitive_word(
    admin: AdminDep,
    word_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除敏感词"""
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    sensitive_word = result.scalar_one_or_none()

    if not sensitive_word:
        raise HTTPException(status_code=404, detail="敏感词不存在")

    await db.delete(sensitive_word)
    await db.commit()

    # 重新加载过滤器
    from services.content_filter_service import init_content_filter

    await init_content_filter(db)

    return ApiResponse(success=True, message="删除成功")


@router.post("/batch", response_model=ApiResponse)
async def batch_create_sensitive_words(
    admin: AdminDep,
    words: List[SensitiveWordCreate],
    db: AsyncSession = Depends(get_db),
):
    """
    批量创建敏感词

    用于快速导入敏感词库
    """
    created_count = 0
    skipped_count = 0

    for word_data in words:
        # 检查是否已存在
        result = await db.execute(
            select(SensitiveWord).where(SensitiveWord.word == word_data.word)
        )
        if result.scalar_one_or_none():
            skipped_count += 1
            continue

        # 创建敏感词
        sensitive_word = SensitiveWord(
            word=word_data.word,
            level=word_data.level,
            category=word_data.category,
            remark=word_data.remark,
            created_by=admin.username,
        )
        db.add(sensitive_word)
        created_count += 1

    await db.commit()

    # 重新加载过滤器
    from services.content_filter_service import init_content_filter

    await init_content_filter(db)

    return ApiResponse(
        success=True,
        message=f"批量创建完成: 新增{created_count}个,跳过{skipped_count}个重复词",
    )


@router.post("/reload", response_model=ApiResponse)
async def reload_sensitive_words(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """
    重新加载敏感词

    用于手动刷新过滤器
    """
    from services.content_filter_service import init_content_filter

    await init_content_filter(db)

    return ApiResponse(success=True, message="敏感词已重新加载")
