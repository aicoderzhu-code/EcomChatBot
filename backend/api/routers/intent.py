"""
意图识别 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.dependencies import DBDep, TenantFlexDep
from schemas import ApiResponse
from services import IntentService, IntentType

router = APIRouter(prefix="/intent", tags=["意图识别"])


class IntentClassifyRequest(BaseModel):
    """意图分类请求，支持 message 或 text 字段"""

    message: str | None = Field(None, description="用户消息")
    text: str | None = Field(None, description="用户消息(兼容)")
    use_llm: bool = False  # 是否使用 LLM

    @property
    def user_message(self) -> str:
        """获取用户输入，优先 message"""
        return self.message or self.text or ""


class EntityExtractRequest(BaseModel):
    """实体提取请求，支持 message 或 text 字段"""

    message: str | None = Field(None, description="用户消息")
    text: str | None = Field(None, description="用户消息(兼容)")
    use_llm: bool = True  # 是否使用 LLM

    @property
    def user_message(self) -> str:
        """获取用户输入，优先 message"""
        return self.message or self.text or ""


@router.post("/classify", response_model=ApiResponse[dict])
async def classify_intent(
    request: IntentClassifyRequest,
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    意图分类接口
    
    支持两种模式：
    - 规则模式：快速，基于关键词匹配
    - 混合模式：规则 + LLM，更准确
    """
    service = IntentService(db, tenant_id)

    msg = request.user_message
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="message 或 text 字段必填")

    if request.use_llm:
        # 混合模式
        result = await service.classify_intent_hybrid(
            user_input=msg,
            use_llm_fallback=True,
        )
    else:
        # 纯规则模式
        intent = service.classify_intent_by_rules(msg)
        confidence = service.get_intent_confidence(msg, intent)

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
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    实体提取接口
    
    从用户消息中提取关键实体
    """
    msg = request.user_message
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="message 或 text 字段必填")

    service = IntentService(db, tenant_id)

    if request.use_llm:
        # 混合模式
        result = await service.extract_entities_hybrid(
            user_input=msg,
            use_llm=True,
        )
    else:
        # 纯规则模式
        entities = service.extract_entities_by_rules(msg)
        result = {
            "entities": entities,
            "method": "rule",
        }

    return ApiResponse(data=result)


@router.get("/intents", response_model=ApiResponse[list[str]])
async def get_available_intents(
    tenant_id: TenantFlexDep,
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
