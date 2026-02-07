"""
对话图节点定义

每个节点是一个独立的处理单元
"""
import logging
from typing import Callable, Any, Optional
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .state import DialogState, ConversationMode

logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """节点基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """节点名称"""
        pass

    @abstractmethod
    async def execute(self, state: DialogState) -> DialogState:
        """执行节点逻辑"""
        pass

    def _trace_node(self, state: DialogState) -> DialogState:
        """记录节点执行"""
        trace = state.get("node_trace", [])
        trace.append(self.name)
        state["node_trace"] = trace
        return state


class ClassificationNode(BaseNode):
    """
    分类节点

    负责对话分类和模式选择
    """

    def __init__(self, intent_service):
        self.intent_service = intent_service

    @property
    def name(self) -> str:
        return "classification"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            # 意图识别
            intent_result = await self.intent_service.classify_intent(
                text=state["user_message"]
            )

            state["intent"] = intent_result.get("intent", "unknown")
            state["intent_confidence"] = intent_result.get("confidence", 0.0)

            # 实体提取
            entities = await self.intent_service.extract_entities(
                text=state["user_message"],
                intent=state["intent"]
            )
            state["entities"] = entities

            # 根据意图自动选择对话模式
            if state.get("mode") is None:
                state["mode"] = self._select_mode(state["intent"])

            logger.debug(f"Classification: intent={state['intent']}, mode={state.get('mode')}")

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            state["error"] = f"分类失败: {str(e)}"
            state["error_node"] = self.name

        return state

    def _select_mode(self, intent: str) -> ConversationMode:
        """根据意图选择对话模式"""
        # 需要知识库的意图
        rag_intents = [
            "order_query", "product_consult", "after_sales",
            "promotion", "faq", "policy_query"
        ]

        # 多步推理意图
        multi_step_intents = [
            "complex_analysis", "comparison", "decision_support"
        ]

        if intent in rag_intents:
            return ConversationMode.RAG
        elif intent in multi_step_intents:
            return ConversationMode.MULTI_STEP
        else:
            return ConversationMode.SIMPLE


class RetrievalNode(BaseNode):
    """
    检索节点

    负责从知识库检索相关内容
    """

    def __init__(self, rag_service, top_k: int = 5):
        self.rag_service = rag_service
        self.top_k = top_k

    @property
    def name(self) -> str:
        return "retrieval"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            # 检索知识
            rag_result = await self.rag_service.query(
                query=state["user_message"],
                top_k=self.top_k,
                tenant_id=state["tenant_id"]
            )

            # 处理检索结果
            results = []
            for item in rag_result.get("results", []):
                results.append({
                    "content": item.get("answer", item.get("content", "")),
                    "score": item.get("score", 0.0),
                    "source": item.get("source", ""),
                    "metadata": item.get("metadata", {}),
                })

            state["retrieval_results"] = results
            logger.debug(f"Retrieved {len(results)} documents")

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            # 检索失败不阻断流程，继续生成
            state["retrieval_results"] = []

        return state


class RerankNode(BaseNode):
    """
    重排序节点

    对检索结果进行重新排序，提高相关性
    """

    def __init__(self, rerank_service, top_k: int = 3, min_score: float = 0.0):
        self.rerank_service = rerank_service
        self.top_k = top_k
        self.min_score = min_score

    @property
    def name(self) -> str:
        return "rerank"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        retrieval_results = state.get("retrieval_results", [])
        if not retrieval_results:
            state["reranked_results"] = []
            return state

        try:
            # 重排序
            reranked = await self.rerank_service.rerank_with_chunks(
                query=state["user_message"],
                chunks=retrieval_results,
                content_key="content",
                top_k=self.top_k,
                min_score=self.min_score,
            )

            state["reranked_results"] = reranked

            # 构建上下文
            context_parts = []
            for item in reranked:
                content = item.get("content", "")
                source = item.get("source", "")
                if source:
                    context_parts.append(f"[来源: {source}]\n{content}")
                else:
                    context_parts.append(content)

            state["context"] = "\n\n".join(context_parts)
            logger.debug(f"Reranked to {len(reranked)} documents")

        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            # 重排序失败，使用原始结果
            state["reranked_results"] = retrieval_results[:self.top_k]
            context_parts = [r.get("content", "") for r in state["reranked_results"]]
            state["context"] = "\n\n".join(context_parts)

        return state


class MemoryNode(BaseNode):
    """
    记忆节点

    负责加载对话历史
    """

    def __init__(self, memory_service_factory, history_limit: int = 10):
        self.memory_service_factory = memory_service_factory
        self.history_limit = history_limit

    @property
    def name(self) -> str:
        return "memory"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            # 创建memory service
            memory_service = self.memory_service_factory(
                state["tenant_id"],
                state["conversation_id"]
            )

            # 获取对话历史
            history = await memory_service.get_conversation_history(
                conversation_id=state["conversation_id"],
                limit=self.history_limit
            )

            # 转换为LangChain消息格式
            messages = []
            for msg in history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
                elif msg.role == "system":
                    messages.append(SystemMessage(content=msg.content))

            # 使用add_messages reducer会自动累积
            state["messages"] = messages

        except Exception as e:
            logger.error(f"Memory loading failed: {e}")
            state["messages"] = []

        return state


class SafetyNode(BaseNode):
    """
    安全检查节点

    对输入或输出进行安全检查
    """

    def __init__(self, check_type: str = "input"):
        """
        Args:
            check_type: "input" 或 "output"
        """
        self.check_type = check_type

    @property
    def name(self) -> str:
        return f"safety_{self.check_type}"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            if self.check_type == "input":
                text = state["user_message"]
                result_key = "input_safety"
            else:
                text = state.get("response", "")
                result_key = "output_safety"

            # 基本安全检查
            safety_result = await self._check_safety(text)

            state[result_key] = {
                "is_safe": safety_result["is_safe"],
                "category": safety_result.get("category"),
                "reason": safety_result.get("reason"),
                "score": safety_result.get("score", 1.0),
            }

            if not safety_result["is_safe"]:
                logger.warning(f"Safety check failed for {self.check_type}: {safety_result}")

        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            state[f"{self.check_type}_safety"] = {"is_safe": True, "score": 0.5}

        return state

    async def _check_safety(self, text: str) -> dict:
        """执行安全检查"""
        # 基本敏感词检查
        sensitive_patterns = [
            "暴力", "色情", "赌博", "毒品", "政治敏感"
        ]

        text_lower = text.lower()
        for pattern in sensitive_patterns:
            if pattern in text_lower:
                return {
                    "is_safe": False,
                    "category": "sensitive_content",
                    "reason": f"检测到敏感内容: {pattern}",
                    "score": 0.0,
                }

        return {"is_safe": True, "score": 1.0}


class GenerationNode(BaseNode):
    """
    生成节点

    负责调用LLM生成回复
    """

    def __init__(
        self,
        llm_service,
        prompt_service,
        model_router=None
    ):
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.model_router = model_router

    @property
    def name(self) -> str:
        return "generation"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            # 获取系统提示词
            system_prompt = await self.prompt_service.get_system_prompt(
                tenant_id=state["tenant_id"]
            )

            # 构建消息列表
            messages = [SystemMessage(content=system_prompt)]

            # 添加历史消息
            for msg in state.get("messages", []):
                messages.append(msg)

            # 构建当前用户消息
            user_content = state["user_message"]

            # 如果有上下文，添加到用户消息中
            context = state.get("context", "")
            if context:
                user_content = f"""请参考以下知识库内容回答问题：

{context}

用户问题: {state['user_message']}

请基于以上信息提供准确的回答。如果知识库内容无法回答问题，请如实告知。"""

            messages.append(HumanMessage(content=user_content))

            # 调用LLM生成
            llm_response = await self.llm_service.generate_response(
                messages=messages,
                tenant_id=state["tenant_id"]
            )

            state["response"] = llm_response.get("content", "")
            state["input_tokens"] = llm_response.get("input_tokens", 0)
            state["output_tokens"] = llm_response.get("output_tokens", 0)
            state["model_used"] = llm_response.get("model", "")
            state["provider_used"] = llm_response.get("provider", "")

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            state["error"] = f"生成失败: {str(e)}"
            state["error_node"] = self.name
            state["response"] = "抱歉，我遇到了一些问题，请稍后再试。"
            state["should_fallback"] = True

        return state


class PostProcessNode(BaseNode):
    """
    后处理节点

    对生成的回复进行后处理
    """

    def __init__(self, max_length: int = 2000):
        self.max_length = max_length

    @property
    def name(self) -> str:
        return "post_process"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        response = state.get("response", "")

        # 长度限制
        if len(response) > self.max_length:
            response = response[:self.max_length] + "..."

        # 清理特殊字符
        response = self._clean_response(response)

        state["response"] = response
        return state

    def _clean_response(self, text: str) -> str:
        """清理回复文本"""
        # 移除多余空行
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 移除首尾空白
        text = text.strip()
        return text


class ErrorHandlingNode(BaseNode):
    """
    错误处理节点

    处理流程中的错误
    """

    def __init__(self, default_response: str = "抱歉，处理您的请求时出现了问题。"):
        self.default_response = default_response

    @property
    def name(self) -> str:
        return "error_handling"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        error = state.get("error", "")
        error_node = state.get("error_node", "unknown")

        logger.error(f"Error in {error_node}: {error}")

        # 如果没有回复，使用默认回复
        if not state.get("response"):
            state["response"] = self.default_response

        return state


class FallbackNode(BaseNode):
    """
    降级节点

    当主流程失败时的降级处理
    """

    def __init__(self, fallback_service=None):
        self.fallback_service = fallback_service

    @property
    def name(self) -> str:
        return "fallback"

    async def execute(self, state: DialogState) -> DialogState:
        state = self._trace_node(state)

        try:
            if self.fallback_service:
                # 使用降级服务
                response = await self.fallback_service.generate_fallback(
                    query=state["user_message"],
                    intent=state.get("intent"),
                )
                state["response"] = response
            else:
                # 基本降级回复
                state["response"] = self._get_fallback_response(state.get("intent"))

        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            state["response"] = "系统繁忙，请稍后再试。"

        return state

    def _get_fallback_response(self, intent: Optional[str]) -> str:
        """获取降级回复"""
        fallback_responses = {
            "order_query": "订单查询服务暂时不可用，请稍后重试或联系客服。",
            "product_consult": "产品咨询服务暂时不可用，请稍后重试。",
            "after_sales": "售后服务暂时不可用，请拨打客服热线。",
        }
        return fallback_responses.get(intent, "服务暂时不可用，请稍后再试。")
