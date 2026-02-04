"""
意图识别 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel

from api.dependencies import DBDep, TenantDep
from schemas import ApiResponse
from services import IntentService, IntentType

router = APIRouter(prefix="/intent", tags=["意图识别"])


class IntentClassifyRequest(BaseModel):
    """意图分类请求"""

    message: str
    use_llm: bool = False  # 是否使用 LLM


class EntityExtractRequest(BaseModel):
    """实体提取请求"""

    message: str
    use_llm: bool = True  # 是否使用 LLM


@router.post("/classify", response_model=ApiResponse[dict])
async def classify_intent(
    request: IntentClassifyRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    意图分类接口
    
    支持两种模式：
    - 规则模式：快速，基于关键词匹配
    - 混合模式：规则 + LLM，更准确
    """
    service = IntentService(db, tenant_id)

    if request.use_llm:
        # 混合模式
        result = await service.classify_intent_hybrid(
            user_input=request.message,
            use_llm_fallback=True,
        )
    else:
        # 纯规则模式
        intent = service.classify_intent_by_rules(request.message)
        confidence = service.get_intent_confidence(request.message, intent)

        result = {
            "intent": intent.value,
            "confidence": "high" if confidence > 0.8 else "medium"
            if confidence > 0.5
            else "low",
            "score": confidence,
            "method": "rule",
        }

    return ApiResponse(data=result)


@router.post("/extract-entities", response_model=ApiResponse[dict])
async def extract_entities(
    request: EntityExtractRequest,
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    实体提取接口
    
    从用户消息中提取关键实体
    """
    service = IntentService(db, tenant_id)

    if request.use_llm:
        # 混合模式
        result = await service.extract_entities_hybrid(
            user_input=request.message,
            use_llm=True,
        )
    else:
        # 纯规则模式
        entities = service.extract_entities_by_rules(request.message)
        result = {
            "entities": entities,
            "method": "rule",
        }

    return ApiResponse(data=result)


@router.get("/intents", response_model=ApiResponse[list[str]])
async def get_available_intents(
    tenant_id: TenantDep,
    db: DBDep,
):
    """
    获取租户可用的意图类型
    
    根据租户订阅的功能模块返回可用意图
    """
    # TODO: 从租户的订阅信息中获取启用的模块
    # 暂时返回所有意图
    intents = [intent.value for intent in IntentType]

    return ApiResponse(data=intents)
