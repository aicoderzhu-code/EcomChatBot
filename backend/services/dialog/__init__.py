"""
对话模块

提供模块化的LangGraph对话流程编排
"""
from .state import (
    DialogState,
    ConversationMode,
    MessageRole,
    IntentInfo,
    RetrievalResult,
    SafetyCheckResult,
    StreamState,
    create_initial_state,
    finalize_state,
)
from .nodes import (
    BaseNode,
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
from .graph import (
    DialogGraphBuilder,
    DialogGraph,
)
from .service import (
    DialogGraphService,
    create_dialog_service,
)

__all__ = [
    # 状态
    "DialogState",
    "ConversationMode",
    "MessageRole",
    "IntentInfo",
    "RetrievalResult",
    "SafetyCheckResult",
    "StreamState",
    "create_initial_state",
    "finalize_state",
    # 节点
    "BaseNode",
    "ClassificationNode",
    "RetrievalNode",
    "RerankNode",
    "MemoryNode",
    "SafetyNode",
    "GenerationNode",
    "PostProcessNode",
    "ErrorHandlingNode",
    "FallbackNode",
    # 图构建器
    "DialogGraphBuilder",
    "DialogGraph",
    # 服务
    "DialogGraphService",
    "create_dialog_service",
]
