"""
对话图构建器

构建不同类型的对话流程图
"""
import logging
from typing import Literal, Optional, Dict, Any, Callable

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import DialogState, ConversationMode, finalize_state
from .nodes import (
    ClassificationNode,
    RetrievalNode,
    RerankNode,
    MemoryNode,
    SafetyNode,
    GenerationNode,
    PostProcessNode,
    ErrorHandlingNode,
    FallbackNode,
)

logger = logging.getLogger(__name__)


class DialogGraphBuilder:
    """
    对话图构建器

    支持多种对话流程：
    - simple: 简单对话（意图识别 -> 生成）
    - rag: RAG增强对话（意图识别 -> 检索 -> 重排序 -> 生成）
    - full: 完整流程（包含安全检查、后处理等）
    """

    def __init__(
        self,
        llm_service,
        intent_service,
        rag_service,
        prompt_service,
        memory_service_factory: Callable,
        rerank_service=None,
        model_router=None,
        fallback_service=None,
    ):
        """
        初始化对话图构建器

        Args:
            llm_service: LLM服务
            intent_service: 意图识别服务
            rag_service: RAG服务
            prompt_service: 提示词服务
            memory_service_factory: 记忆服务工厂函数
            rerank_service: 重排序服务（可选）
            model_router: 模型路由器（可选）
            fallback_service: 降级服务（可选）
        """
        self.llm_service = llm_service
        self.intent_service = intent_service
        self.rag_service = rag_service
        self.prompt_service = prompt_service
        self.memory_service_factory = memory_service_factory
        self.rerank_service = rerank_service
        self.model_router = model_router
        self.fallback_service = fallback_service

        # 创建节点实例
        self._init_nodes()

    def _init_nodes(self):
        """初始化节点"""
        self.classification_node = ClassificationNode(self.intent_service)
        self.retrieval_node = RetrievalNode(self.rag_service, top_k=5)
        self.memory_node = MemoryNode(self.memory_service_factory, history_limit=10)
        self.generation_node = GenerationNode(
            self.llm_service,
            self.prompt_service,
            self.model_router
        )
        self.post_process_node = PostProcessNode()
        self.error_handling_node = ErrorHandlingNode()
        self.fallback_node = FallbackNode(self.fallback_service)
        self.input_safety_node = SafetyNode(check_type="input")
        self.output_safety_node = SafetyNode(check_type="output")

        if self.rerank_service:
            self.rerank_node = RerankNode(self.rerank_service, top_k=3)
        else:
            self.rerank_node = None

    def build_simple_graph(self) -> StateGraph:
        """
        构建简单对话图

        流程: 分类 -> 记忆加载 -> 生成 -> 后处理 -> END
        """
        workflow = StateGraph(DialogState)

        # 添加节点
        workflow.add_node("classification", self.classification_node.execute)
        workflow.add_node("memory", self.memory_node.execute)
        workflow.add_node("generation", self.generation_node.execute)
        workflow.add_node("post_process", self.post_process_node.execute)
        workflow.add_node("finalize", finalize_state)
        workflow.add_node("error_handling", self.error_handling_node.execute)

        # 设置入口点
        workflow.set_entry_point("classification")

        # 添加边
        workflow.add_conditional_edges(
            "classification",
            self._check_error,
            {"continue": "memory", "error": "error_handling"}
        )
        workflow.add_edge("memory", "generation")
        workflow.add_conditional_edges(
            "generation",
            self._check_error,
            {"continue": "post_process", "error": "error_handling"}
        )
        workflow.add_edge("post_process", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("error_handling", "finalize")

        return workflow.compile()

    def build_rag_graph(self) -> StateGraph:
        """
        构建RAG增强对话图

        流程: 分类 -> 记忆加载 -> 检索 -> [重排序] -> 生成 -> 后处理 -> END
        """
        workflow = StateGraph(DialogState)

        # 添加节点
        workflow.add_node("classification", self.classification_node.execute)
        workflow.add_node("memory", self.memory_node.execute)
        workflow.add_node("retrieval", self.retrieval_node.execute)
        if self.rerank_node:
            workflow.add_node("rerank", self.rerank_node.execute)
        workflow.add_node("generation", self.generation_node.execute)
        workflow.add_node("post_process", self.post_process_node.execute)
        workflow.add_node("finalize", finalize_state)
        workflow.add_node("error_handling", self.error_handling_node.execute)

        # 设置入口点
        workflow.set_entry_point("classification")

        # 添加边
        workflow.add_conditional_edges(
            "classification",
            self._check_error,
            {"continue": "memory", "error": "error_handling"}
        )
        workflow.add_edge("memory", "retrieval")

        if self.rerank_node:
            workflow.add_edge("retrieval", "rerank")
            workflow.add_edge("rerank", "generation")
        else:
            workflow.add_edge("retrieval", "generation")

        workflow.add_conditional_edges(
            "generation",
            self._check_error,
            {"continue": "post_process", "error": "error_handling"}
        )
        workflow.add_edge("post_process", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("error_handling", "finalize")

        return workflow.compile()

    def build_full_graph(self) -> StateGraph:
        """
        构建完整对话图（带安全检查和降级）

        流程:
        输入安全检查 -> 分类 -> 记忆加载 -> [检索 -> 重排序] -> 生成
        -> 输出安全检查 -> 后处理 -> END

        带有错误处理和降级逻辑
        """
        workflow = StateGraph(DialogState)

        # 添加所有节点
        workflow.add_node("input_safety", self.input_safety_node.execute)
        workflow.add_node("classification", self.classification_node.execute)
        workflow.add_node("memory", self.memory_node.execute)
        workflow.add_node("retrieval", self.retrieval_node.execute)
        if self.rerank_node:
            workflow.add_node("rerank", self.rerank_node.execute)
        workflow.add_node("generation", self.generation_node.execute)
        workflow.add_node("output_safety", self.output_safety_node.execute)
        workflow.add_node("post_process", self.post_process_node.execute)
        workflow.add_node("finalize", finalize_state)
        workflow.add_node("error_handling", self.error_handling_node.execute)
        workflow.add_node("fallback", self.fallback_node.execute)

        # 设置入口点
        workflow.set_entry_point("input_safety")

        # 添加边
        workflow.add_conditional_edges(
            "input_safety",
            self._check_input_safety,
            {"safe": "classification", "unsafe": "error_handling"}
        )

        workflow.add_conditional_edges(
            "classification",
            self._route_by_mode,
            {
                "simple": "memory",
                "rag": "memory",
                "error": "error_handling"
            }
        )

        workflow.add_conditional_edges(
            "memory",
            self._should_retrieve,
            {"retrieve": "retrieval", "skip": "generation"}
        )

        if self.rerank_node:
            workflow.add_edge("retrieval", "rerank")
            workflow.add_edge("rerank", "generation")
        else:
            workflow.add_edge("retrieval", "generation")

        workflow.add_conditional_edges(
            "generation",
            self._check_generation,
            {
                "success": "output_safety",
                "error": "fallback"
            }
        )

        workflow.add_edge("fallback", "output_safety")

        workflow.add_conditional_edges(
            "output_safety",
            self._check_output_safety,
            {"safe": "post_process", "unsafe": "error_handling"}
        )

        workflow.add_edge("post_process", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("error_handling", "finalize")

        return workflow.compile()

    def build_adaptive_graph(self) -> StateGraph:
        """
        构建自适应对话图

        根据分类结果动态选择流程路径
        """
        workflow = StateGraph(DialogState)

        # 添加节点
        workflow.add_node("classification", self.classification_node.execute)
        workflow.add_node("memory", self.memory_node.execute)
        workflow.add_node("retrieval", self.retrieval_node.execute)
        if self.rerank_node:
            workflow.add_node("rerank", self.rerank_node.execute)
        workflow.add_node("generation", self.generation_node.execute)
        workflow.add_node("post_process", self.post_process_node.execute)
        workflow.add_node("finalize", finalize_state)
        workflow.add_node("error_handling", self.error_handling_node.execute)

        # 设置入口点
        workflow.set_entry_point("classification")

        # 自适应路由
        workflow.add_conditional_edges(
            "classification",
            self._adaptive_route,
            {
                "simple": "memory",
                "rag": "memory",
                "error": "error_handling"
            }
        )

        # Simple模式直接到生成
        workflow.add_conditional_edges(
            "memory",
            self._should_retrieve,
            {"retrieve": "retrieval", "skip": "generation"}
        )

        if self.rerank_node:
            workflow.add_edge("retrieval", "rerank")
            workflow.add_edge("rerank", "generation")
        else:
            workflow.add_edge("retrieval", "generation")

        workflow.add_conditional_edges(
            "generation",
            self._check_error,
            {"continue": "post_process", "error": "error_handling"}
        )

        workflow.add_edge("post_process", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("error_handling", "finalize")

        return workflow.compile()

    # ========== 路由函数 ==========

    def _check_error(self, state: DialogState) -> Literal["continue", "error"]:
        """检查是否有错误"""
        if state.get("error"):
            return "error"
        return "continue"

    def _check_input_safety(self, state: DialogState) -> Literal["safe", "unsafe"]:
        """检查输入安全"""
        safety = state.get("input_safety", {})
        if safety.get("is_safe", True):
            return "safe"
        return "unsafe"

    def _check_output_safety(self, state: DialogState) -> Literal["safe", "unsafe"]:
        """检查输出安全"""
        safety = state.get("output_safety", {})
        if safety.get("is_safe", True):
            return "safe"
        return "unsafe"

    def _route_by_mode(self, state: DialogState) -> Literal["simple", "rag", "error"]:
        """根据模式路由"""
        if state.get("error"):
            return "error"

        mode = state.get("mode", ConversationMode.SIMPLE)
        if mode == ConversationMode.RAG:
            return "rag"
        return "simple"

    def _should_retrieve(self, state: DialogState) -> Literal["retrieve", "skip"]:
        """决定是否需要检索"""
        mode = state.get("mode", ConversationMode.SIMPLE)
        if mode == ConversationMode.RAG:
            return "retrieve"
        return "skip"

    def _check_generation(self, state: DialogState) -> Literal["success", "error"]:
        """检查生成是否成功"""
        if state.get("should_fallback") or state.get("error"):
            return "error"
        if not state.get("response"):
            return "error"
        return "success"

    def _adaptive_route(self, state: DialogState) -> Literal["simple", "rag", "error"]:
        """自适应路由"""
        if state.get("error"):
            return "error"

        # 根据意图置信度和类型决定
        intent = state.get("intent", "unknown")
        confidence = state.get("intent_confidence", 0.0)

        # 低置信度使用简单模式
        if confidence < 0.5:
            return "simple"

        # RAG意图列表
        rag_intents = [
            "order_query", "product_consult", "after_sales",
            "promotion", "faq", "policy_query"
        ]

        if intent in rag_intents:
            return "rag"

        return "simple"


class DialogGraph:
    """
    对话图包装类

    提供统一的对话处理接口
    """

    def __init__(
        self,
        graph: StateGraph,
        checkpointer: Optional[MemorySaver] = None
    ):
        self.graph = graph
        self.checkpointer = checkpointer

    async def process(
        self,
        state: DialogState,
        config: Optional[Dict[str, Any]] = None
    ) -> DialogState:
        """
        处理对话

        Args:
            state: 初始状态
            config: 配置（如thread_id用于状态持久化）

        Returns:
            最终状态
        """
        config = config or {}
        result = await self.graph.ainvoke(state, config=config)
        return result

    async def stream(
        self,
        state: DialogState,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        流式处理对话

        Args:
            state: 初始状态
            config: 配置

        Yields:
            流式更新
        """
        config = config or {}
        async for update in self.graph.astream(state, config=config):
            yield update
