"""
基于 LangGraph 的对话流程编排服务
"""
from typing import TypedDict, Annotated, Literal
from typing_extensions import NotRequired
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

# 直接导入避免循环依赖
from services.llm_service import LLMService
from services.intent_service import IntentService
from services.rag_service import RAGService
from services.prompt_service import PromptService
from services.memory_service import MemoryService

from core.exceptions import AppException


class DialogState(TypedDict):
    """对话状态"""
    # 输入
    user_message: str
    conversation_id: str
    tenant_id: str
    use_rag: bool

    # 中间状态
    intent: NotRequired[str]
    intent_confidence: NotRequired[float]
    entities: NotRequired[dict]
    context: NotRequired[str]
    rag_context: NotRequired[str]

    # 输出
    response: NotRequired[str]
    input_tokens: NotRequired[int]
    output_tokens: NotRequired[int]
    error: NotRequired[str]


class DialogGraphService:
    """
    基于 LangGraph 的对话流程服务

    实现完整的对话流程编排：
    1. 意图识别
    2. 实体提取
    3. 知识检索 (RAG)
    4. LLM生成
    5. 后处理
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

        # 初始化各个服务（修复：不再将 db 误传为 tenant_id）
        self.llm_service = LLMService(tenant_id)
        self.intent_service = IntentService(db, tenant_id)
        self.rag_service = RAGService(db, tenant_id)
        self.prompt_service = PromptService()
        # MemoryService需要conversation_id，在处理消息时动态创建
        self.memory_service = None

        # 构建对话图
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建对话流程图"""
        # 创建状态图
        workflow = StateGraph(DialogState)

        # 添加节点
        workflow.add_node("intent_recognition", self._intent_recognition_node)
        workflow.add_node("knowledge_retrieval", self._knowledge_retrieval_node)
        workflow.add_node("response_generation", self._response_generation_node)
        workflow.add_node("error_handling", self._error_handling_node)

        # 设置入口点
        workflow.set_entry_point("intent_recognition")

        # 添加条件边
        workflow.add_conditional_edges(
            "intent_recognition",
            self._should_use_rag,
            {
                "use_rag": "knowledge_retrieval",
                "no_rag": "response_generation",
                "error": "error_handling"
            }
        )

        workflow.add_edge("knowledge_retrieval", "response_generation")
        workflow.add_edge("response_generation", END)
        workflow.add_edge("error_handling", END)

        # 编译图
        return workflow.compile()

    async def _intent_recognition_node(self, state: DialogState) -> DialogState:
        """意图识别节点"""
        try:
            # 识别意图
            intent_result = await self.intent_service.classify_intent(
                text=state["user_message"]
            )

            # 提取实体
            entities = await self.intent_service.extract_entities(
                text=state["user_message"],
                intent=intent_result["intent"]
            )

            state["intent"] = intent_result["intent"]
            state["intent_confidence"] = intent_result["confidence"]
            state["entities"] = entities

            return state

        except Exception as e:
            state["error"] = f"意图识别失败: {str(e)}"
            return state

    async def _knowledge_retrieval_node(self, state: DialogState) -> DialogState:
        """知识检索节点"""
        try:
            # 使用RAG检索相关知识
            rag_result = await self.rag_service.query(
                query=state["user_message"],
                top_k=3,
                tenant_id=state["tenant_id"]
            )

            # 构建上下文
            context_parts = []
            if rag_result.get("results"):
                for item in rag_result["results"][:3]:
                    context_parts.append(f"- {item.get('answer', item.get('content', ''))}")

            state["rag_context"] = "\n".join(context_parts)
            return state

        except Exception as e:
            # RAG失败不影响主流程，继续生成回复
            state["rag_context"] = ""
            return state

    async def _response_generation_node(self, state: DialogState) -> DialogState:
        """回复生成节点"""
        try:
            # 动态创建MemoryService（需要conversation_id）
            from services.memory_service import MemoryService
            memory_service = MemoryService(self.db, self.tenant_id, state["conversation_id"])

            # 获取对话历史作为上下文
            history = await memory_service.get_conversation_history(
                conversation_id=state["conversation_id"],
                limit=5
            )

            # 构建系统提示词
            system_prompt = await self.prompt_service.get_system_prompt(
                tenant_id=state["tenant_id"]
            )

            # 构建完整提示词
            messages = [SystemMessage(content=system_prompt)]

            # 添加历史对话
            for msg in history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))

            # 添加当前用户消息
            messages.append(HumanMessage(content=state["user_message"]))

            # 如果有RAG上下文，添加到提示词中
            if state.get("rag_context"):
                rag_instruction = f"\n\n参考以下知识库内容回答问题：\n{state['rag_context']}\n\n请基于以上信息回答用户问题。"
                messages[-1] = HumanMessage(content=state["user_message"] + rag_instruction)

            # 调用LLM生成回复
            llm_response = await self.llm_service.generate_response(
                messages=messages,
                tenant_id=state["tenant_id"]
            )

            state["response"] = llm_response["content"]
            state["input_tokens"] = llm_response.get("input_tokens", 0)
            state["output_tokens"] = llm_response.get("output_tokens", 0)

            return state

        except Exception as e:
            state["error"] = f"生成回复失败: {str(e)}"
            state["response"] = "抱歉，我遇到了一些问题，请稍后再试。"
            return state

    async def _error_handling_node(self, state: DialogState) -> DialogState:
        """错误处理节点"""
        if not state.get("response"):
            state["response"] = "抱歉，处理您的请求时出现了问题。"
        return state

    def _should_use_rag(self, state: DialogState) -> Literal["use_rag", "no_rag", "error"]:
        """决定是否使用RAG"""
        if state.get("error"):
            return "error"

        # 检查是否启用RAG
        if not state.get("use_rag", False):
            return "no_rag"

        # 根据意图决定是否使用知识库
        intent = state.get("intent", "")

        # 以下意图类型适合使用知识库检索
        rag_intents = ["order_query", "product_consult", "after_sales", "promotion"]

        if intent in rag_intents:
            return "use_rag"

        return "no_rag"

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = False
    ) -> dict:
        """
        处理用户消息（完整对话流程）

        Args:
            conversation_id: 会话ID
            user_message: 用户消息
            use_rag: 是否使用RAG检索

        Returns:
            dict: {
                "response": str,
                "intent": str,
                "entities": dict,
                "input_tokens": int,
                "output_tokens": int,
                "total_tokens": int
            }
        """
        # 从数据库加载默认 LLM 配置（优先于环境变量）
        try:
            from services.model_config_service import ModelConfigService
            model_config = await ModelConfigService(self.db, self.tenant_id).get_default_model(use_case="dialogue")
            if model_config:
                self.llm_service = LLMService(self.tenant_id, model_config=model_config)
        except Exception:
            pass

        # 初始化状态
        initial_state: DialogState = {
            "user_message": user_message,
            "conversation_id": conversation_id,
            "tenant_id": self.tenant_id,
            "use_rag": use_rag
        }

        # 执行对话流程
        final_state = await self.graph.ainvoke(initial_state)

        # 返回结果
        return {
            "response": final_state.get("response", ""),
            "intent": final_state.get("intent", "unknown"),
            "entities": final_state.get("entities", {}),
            "input_tokens": final_state.get("input_tokens", 0),
            "output_tokens": final_state.get("output_tokens", 0),
            "total_tokens": (
                final_state.get("input_tokens", 0) +
                final_state.get("output_tokens", 0)
            )
        }

    async def stream_message(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = False
    ):
        """
        流式处理用户消息（用于WebSocket）

        Args:
            conversation_id: 会话ID
            user_message: 用户消息
            use_rag: 是否使用RAG检索

        Yields:
            str: 流式输出的文本片段
        """
        # 初始化状态
        initial_state: DialogState = {
            "user_message": user_message,
            "conversation_id": conversation_id,
            "tenant_id": self.tenant_id,
            "use_rag": use_rag
        }

        # 异步执行流程并流式输出
        async for chunk in self.graph.astream(initial_state):
            if "response_generation" in chunk:
                # 这里可以接入LLM的流式输出
                # 暂时使用完整输出
                pass
            elif "error" in chunk:
                yield chunk.get("error", "")

        # 如果没有流式输出，返回完整回复
        final_state = await self.graph.ainvoke(initial_state)
        yield final_state.get("response", "")
