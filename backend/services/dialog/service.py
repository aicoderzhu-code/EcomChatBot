"""
对话图服务

提供高级API，封装对话图的使用
"""
import logging
from typing import Optional, Dict, Any, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession

from .state import DialogState, ConversationMode, create_initial_state
from .graph import DialogGraphBuilder, DialogGraph

logger = logging.getLogger(__name__)


class DialogGraphService:
    """
    对话图服务

    提供高级API封装对话流程，支持多种对话模式
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        graph_type: str = "adaptive"
    ):
        """
        初始化对话图服务

        Args:
            db: 数据库会话
            tenant_id: 租户ID
            graph_type: 图类型 (simple/rag/full/adaptive)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.graph_type = graph_type

        # 延迟初始化服务和图
        self._graph: Optional[DialogGraph] = None
        self._builder: Optional[DialogGraphBuilder] = None

    async def _init_services(self):
        """初始化依赖服务"""
        # 导入避免循环依赖
        from services.llm_service import LLMService
        from services.intent_service import IntentService
        from services.rag_service import RAGService
        from services.prompt_service import PromptService
        from services.memory_service import MemoryService

        # 创建服务实例（修复：不再将 db 误传为 tenant_id）
        llm_service = LLMService(self.tenant_id)
        intent_service = IntentService(self.db, self.tenant_id)
        rag_service = RAGService(self.db, self.tenant_id)
        prompt_service = PromptService()

        # Memory服务工厂（需要conversation_id）
        def memory_service_factory(tenant_id: str, conversation_id: str):
            return MemoryService(self.db, tenant_id, conversation_id)

        # 尝试加载rerank服务
        rerank_service = None
        try:
            from services.rerank_service import get_rerank_service
            rerank_service = get_rerank_service()
            if not rerank_service.get_available_providers():
                rerank_service = None
        except Exception:
            pass

        # 尝试加载模型路由器
        model_router = None
        try:
            from services.llm.router import get_model_router
            router = get_model_router()
            if router._initialized:
                model_router = router
        except Exception:
            pass

        # 创建构建器
        self._builder = DialogGraphBuilder(
            llm_service=llm_service,
            intent_service=intent_service,
            rag_service=rag_service,
            prompt_service=prompt_service,
            memory_service_factory=memory_service_factory,
            rerank_service=rerank_service,
            model_router=model_router,
        )

    async def _get_graph(self) -> DialogGraph:
        """获取或创建对话图"""
        if self._graph is None:
            await self._init_services()

            # 根据类型构建图
            if self.graph_type == "simple":
                compiled = self._builder.build_simple_graph()
            elif self.graph_type == "rag":
                compiled = self._builder.build_rag_graph()
            elif self.graph_type == "full":
                compiled = self._builder.build_full_graph()
            else:  # adaptive
                compiled = self._builder.build_adaptive_graph()

            self._graph = DialogGraph(compiled)

        return self._graph

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = False,
        mode: Optional[ConversationMode] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            conversation_id: 会话ID
            user_message: 用户消息
            use_rag: 是否使用RAG检索
            mode: 对话模式（可选，不指定则自动选择）

        Returns:
            dict: {
                "response": str,
                "intent": str,
                "entities": dict,
                "input_tokens": int,
                "output_tokens": int,
                "total_tokens": int,
                "latency_ms": float,
                "model_used": str,
                "provider_used": str
            }
        """
        graph = await self._get_graph()

        # 确定对话模式
        if mode is None:
            mode = ConversationMode.RAG if use_rag else ConversationMode.SIMPLE

        # 创建初始状态
        initial_state = create_initial_state(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            user_message=user_message,
            mode=mode,
        )

        # 执行对话流程
        final_state = await graph.process(initial_state)

        # 返回结果
        return {
            "response": final_state.get("response", ""),
            "intent": final_state.get("intent", "unknown"),
            "entities": final_state.get("entities", {}),
            "input_tokens": final_state.get("input_tokens", 0),
            "output_tokens": final_state.get("output_tokens", 0),
            "total_tokens": final_state.get("total_tokens", 0),
            "latency_ms": final_state.get("latency_ms", 0),
            "model_used": final_state.get("model_used", ""),
            "provider_used": final_state.get("provider_used", ""),
            "node_trace": final_state.get("node_trace", []),
            "error": final_state.get("error"),
        }

    async def stream_message(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = False,
        mode: Optional[ConversationMode] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式处理用户消息

        Args:
            conversation_id: 会话ID
            user_message: 用户消息
            use_rag: 是否使用RAG检索
            mode: 对话模式

        Yields:
            dict: 流式更新 {
                "node": str,
                "content": str,
                "is_final": bool
            }
        """
        graph = await self._get_graph()

        # 确定对话模式
        if mode is None:
            mode = ConversationMode.RAG if use_rag else ConversationMode.SIMPLE

        # 创建初始状态
        initial_state = create_initial_state(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            user_message=user_message,
            mode=mode,
        )

        # 流式执行
        async for update in graph.stream(initial_state):
            for node_name, node_output in update.items():
                if node_name == "generation" and "response" in node_output:
                    yield {
                        "node": node_name,
                        "content": node_output.get("response", ""),
                        "is_final": False,
                    }

        # 最终结果
        yield {
            "node": "finalize",
            "content": "",
            "is_final": True,
        }

    async def quick_chat(
        self,
        conversation_id: str,
        user_message: str
    ) -> str:
        """
        快速对话（简化接口）

        Args:
            conversation_id: 会话ID
            user_message: 用户消息

        Returns:
            回复文本
        """
        result = await self.process_message(
            conversation_id=conversation_id,
            user_message=user_message,
            use_rag=False,
            mode=ConversationMode.SIMPLE
        )
        return result.get("response", "")

    async def rag_chat(
        self,
        conversation_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        RAG对话

        Args:
            conversation_id: 会话ID
            user_message: 用户消息

        Returns:
            完整回复结果
        """
        return await self.process_message(
            conversation_id=conversation_id,
            user_message=user_message,
            use_rag=True,
            mode=ConversationMode.RAG
        )


# 便捷函数
async def create_dialog_service(
    db: AsyncSession,
    tenant_id: str,
    graph_type: str = "adaptive"
) -> DialogGraphService:
    """
    创建对话图服务

    Args:
        db: 数据库会话
        tenant_id: 租户ID
        graph_type: 图类型

    Returns:
        DialogGraphService实例
    """
    return DialogGraphService(db, tenant_id, graph_type)
