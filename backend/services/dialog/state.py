"""
对话状态定义

使用 TypedDict 和 Annotated 定义 LangGraph 状态
"""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from typing_extensions import NotRequired
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationMode(str, Enum):
    """对话模式"""
    SIMPLE = "simple"           # 简单对话
    RAG = "rag"                 # RAG增强对话
    MULTI_STEP = "multi_step"   # 多步推理
    TASK = "task"               # 任务型对话


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class IntentInfo:
    """意图信息"""
    intent: str
    confidence: float
    sub_intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    is_safe: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    score: float = 1.0


class DialogState(TypedDict):
    """
    对话状态

    使用 Annotated 支持状态累积
    """
    # === 基础信息 ===
    tenant_id: str
    conversation_id: str
    session_id: NotRequired[str]
    user_id: NotRequired[str]

    # === 消息历史（使用add_messages reducer累积） ===
    messages: Annotated[List[BaseMessage], add_messages]

    # === 当前输入 ===
    user_message: str
    mode: NotRequired[ConversationMode]

    # === 意图识别结果 ===
    intent: NotRequired[str]
    intent_confidence: NotRequired[float]
    sub_intent: NotRequired[str]
    entities: NotRequired[Dict[str, Any]]

    # === 检索结果 ===
    retrieval_results: NotRequired[List[Dict[str, Any]]]
    reranked_results: NotRequired[List[Dict[str, Any]]]
    context: NotRequired[str]

    # === 安全检查 ===
    input_safety: NotRequired[Dict[str, Any]]
    output_safety: NotRequired[Dict[str, Any]]

    # === 生成结果 ===
    response: NotRequired[str]
    model_used: NotRequired[str]
    provider_used: NotRequired[str]

    # === Token统计 ===
    input_tokens: NotRequired[int]
    output_tokens: NotRequired[int]
    total_tokens: NotRequired[int]

    # === 元数据 ===
    start_time: NotRequired[float]
    end_time: NotRequired[float]
    latency_ms: NotRequired[float]
    node_trace: NotRequired[List[str]]

    # === 错误处理 ===
    error: NotRequired[str]
    error_node: NotRequired[str]
    should_fallback: NotRequired[bool]


class StreamState(TypedDict):
    """流式输出状态"""
    chunk: str
    is_final: bool
    node: str


def create_initial_state(
    tenant_id: str,
    conversation_id: str,
    user_message: str,
    mode: ConversationMode = ConversationMode.RAG,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> DialogState:
    """
    创建初始对话状态

    Args:
        tenant_id: 租户ID
        conversation_id: 会话ID
        user_message: 用户消息
        mode: 对话模式
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        初始化的DialogState
    """
    import time

    state: DialogState = {
        "tenant_id": tenant_id,
        "conversation_id": conversation_id,
        "user_message": user_message,
        "messages": [],
        "mode": mode,
        "start_time": time.time(),
        "node_trace": [],
    }

    if user_id:
        state["user_id"] = user_id
    if session_id:
        state["session_id"] = session_id

    return state


def finalize_state(state: DialogState) -> DialogState:
    """
    完成对话状态（计算最终指标）

    Args:
        state: 对话状态

    Returns:
        更新后的状态
    """
    import time

    state["end_time"] = time.time()
    if state.get("start_time"):
        state["latency_ms"] = (state["end_time"] - state["start_time"]) * 1000

    # 计算总token
    input_tokens = state.get("input_tokens", 0)
    output_tokens = state.get("output_tokens", 0)
    state["total_tokens"] = input_tokens + output_tokens

    return state
