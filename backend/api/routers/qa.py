"""
QA 对管理 API 路由
"""
import csv
import io
import logging

from fastapi import APIRouter, Query, UploadFile, File
from pydantic import BaseModel

from api.dependencies import DBDep, TenantFlexDep
from api.middleware import ApiQuotaDep
from schemas.base import ApiResponse, PaginatedResponse
from schemas.qa import QAPairCreate, QAPairResponse, QAPairUpdate
from services.qa_service import QAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/qa", tags=["QA对管理"])


@router.post("", response_model=ApiResponse[QAPairResponse])
async def create_qa_pair(
    data: QAPairCreate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """创建 QA 对（自动生成相似问变体）"""
    service = QAService(db, tenant_id)
    qa_pair = await service.create_qa_pair(
        question=data.question,
        answer=data.answer,
        category=data.category,
        priority=data.priority,
        knowledge_id=data.knowledge_id,
    )
    return ApiResponse(data=qa_pair)


@router.get("", response_model=ApiResponse[PaginatedResponse[QAPairResponse]])
async def list_qa_pairs(
    tenant_id: TenantFlexDep,
    db: DBDep,
    category: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """查询 QA 对列表"""
    service = QAService(db, tenant_id)
    qa_list, total = await service.list_qa_pairs(
        category=category,
        keyword=keyword,
        status=status,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(
        items=qa_list, total=total, page=page, size=size,
    )
    return ApiResponse(data=paginated)


@router.get("/popular", response_model=ApiResponse[list[QAPairResponse]])
async def get_popular_qa(
    tenant_id: TenantFlexDep,
    db: DBDep,
    category: str | None = None,
    limit: int = Query(10, ge=1, le=50),
):
    """获取热门 QA 对"""
    service = QAService(db, tenant_id)
    qa_list = await service.get_popular_qa(category=category, limit=limit)
    return ApiResponse(data=qa_list)


@router.post("/import", response_model=ApiResponse[dict])
async def import_qa_from_csv(
    file: UploadFile = File(...),
    tenant_id: TenantFlexDep = None,
    db: DBDep = None,
):
    """
    CSV 批量导入 QA 对

    CSV 格式：question,answer,category（第一行为表头）
    """
    from fastapi import HTTPException

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk")

    reader = csv.DictReader(io.StringIO(text))
    items = []
    for row in reader:
        if "question" not in row or "answer" not in row:
            raise HTTPException(status_code=400, detail="CSV 必须包含 question 和 answer 列")
        items.append({
            "question": row["question"].strip(),
            "answer": row["answer"].strip(),
            "category": row.get("category", "").strip() or None,
        })

    if not items:
        raise HTTPException(status_code=400, detail="CSV 文件为空")

    service = QAService(db, tenant_id)
    results = await service.import_from_list(items)

    return ApiResponse(data={
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "failed_items": results["failed"] if results["failed"] else None,
    })


@router.post("/{qa_id}/regenerate-variations", response_model=ApiResponse[QAPairResponse])
async def regenerate_variations(
    qa_id: str,
    tenant_id: ApiQuotaDep,
    db: DBDep,
):
    """重新生成相似问变体"""
    service = QAService(db, tenant_id)
    qa_pair = await service.get_qa_pair(qa_id)
    variations = await service.generate_variations(qa_pair.question)
    qa_pair = await service.update_qa_pair(qa_id, variations=variations)
    return ApiResponse(data=qa_pair)


@router.get("/{qa_id}", response_model=ApiResponse[QAPairResponse])
async def get_qa_pair(
    qa_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """获取 QA 对详情"""
    service = QAService(db, tenant_id)
    qa_pair = await service.get_qa_pair(qa_id)
    return ApiResponse(data=qa_pair)


@router.put("/{qa_id}", response_model=ApiResponse[QAPairResponse])
async def update_qa_pair(
    qa_id: str,
    data: QAPairUpdate,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """更新 QA 对"""
    service = QAService(db, tenant_id)
    qa_pair = await service.update_qa_pair(
        qa_id=qa_id,
        question=data.question,
        answer=data.answer,
        category=data.category,
        priority=data.priority,
        variations=data.variations,
        status=data.status,
    )
    return ApiResponse(data=qa_pair)


@router.delete("/{qa_id}", response_model=ApiResponse[dict])
async def delete_qa_pair(
    qa_id: str,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """删除 QA 对"""
    service = QAService(db, tenant_id)
    await service.delete_qa_pair(qa_id)
    return ApiResponse(data={"message": "删除成功"})
