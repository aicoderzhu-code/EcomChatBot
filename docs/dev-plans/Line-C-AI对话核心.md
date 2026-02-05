# Line C: AI对话核心开发计划

> 负责领域: LangGraph对话编排、RAG系统、多模型支持
> 核心技能: LangChain、LangGraph、向量检索、提示工程
> 总周期: Week 2-9

---

## 一、开发线概述

### 1.1 职责范围

Line C 负责AI对话的核心能力，包括：
- LangGraph对话流程编排
- 上下文记忆管理
- RAG检索增强生成
- 多LLM适配与路由

### 1.2 阶段规划

| 阶段 | 周期 | 主要任务 | 交付目标 |
|------|------|----------|----------|
| 第一阶段 | Week 2 | 对话流程编排 | LangGraph工作流、状态管理 |
| 第二阶段 | Week 3-5 | RAG系统完善 | 多租户隔离、完整RAG流程 |
| 第三阶段 | Week 7-9 | 多模型支持 | LLM适配器、智能路由 |

### 1.3 依赖关系

```
Line C 输出 (被其他线依赖):
├── 对话API → Line E 监控指标采集
├── 对话事件 → Line A Webhook发布
└── Token消耗数据 → Line B 计费使用

Line C 输入 (依赖其他线):
├── Line A: 认证中间件 (获取tenant_id)
├── Line B: 配额检查装饰器
└── Line E: 敏感词过滤服务
```

---

## 二、第一阶段：对话流程编排 (Week 2)

### 2.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| C1.1 | LangGraph状态定义 | P0 | 0.5天 | 待开始 |
| C1.2 | LangGraph节点实现 | P0 | 2天 | 待开始 |
| C1.3 | LangGraph边定义 | P0 | 1天 | 待开始 |
| C1.4 | 对话图编排 | P0 | 1天 | 待开始 |
| C1.5 | 上下文滑动窗口 | P1 | 1天 | 待开始 |
| C1.6 | 集成测试 | P1 | 0.5天 | 待开始 |

### 2.2 详细设计

#### C1.1 LangGraph状态定义

**文件**: `backend/services/graph/state.py` (新建)

```python
from typing import TypedDict, Annotated, List, Optional, Any
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from enum import Enum
from datetime import datetime

class IntentType(Enum):
    """意图类型"""
    ORDER_QUERY = "order_query"           # 订单查询
    PRODUCT_CONSULT = "product_consult"   # 商品咨询
    AFTER_SALES = "after_sales"           # 售后服务
    PAYMENT_ISSUE = "payment_issue"       # 支付问题
    LOGISTICS_QUERY = "logistics_query"   # 物流查询
    COMPLAINT = "complaint"               # 投诉建议
    PROMOTION = "promotion"               # 促销咨询
    ACCOUNT_ISSUE = "account_issue"       # 账户问题
    GENERAL = "general"                   # 一般咨询
    HUMAN_TRANSFER = "human_transfer"     # 转人工

class ConversationState(TypedDict):
    """
    对话状态

    LangGraph通过状态在节点间传递数据
    使用Annotated和add_messages支持消息累积
    """
    # 基础信息
    tenant_id: str
    conversation_id: str
    customer_id: str

    # 消息历史 (使用add_messages支持累积)
    messages: Annotated[List[BaseMessage], add_messages]

    # 当前用户输入
    user_input: str

    # 意图识别结果
    intent: Optional[IntentType]
    intent_confidence: float
    entities: dict  # 提取的实体 {"order_id": "xxx", "product_name": "xxx"}

    # 知识检索结果
    retrieved_documents: List[dict]
    retrieval_scores: List[float]

    # 外部数据(订单、商品等)
    external_data: dict

    # 生成的回复
    response: str
    response_sources: List[str]  # 引用来源

    # 流程控制
    current_node: str
    requires_human: bool
    error: Optional[str]

    # 元数据
    turn_count: int
    started_at: datetime
    tokens_used: dict  # {"input": 0, "output": 0}

class ConversationConfig(TypedDict):
    """对话配置"""
    max_turns: int                    # 最大轮次
    max_context_tokens: int           # 最大上下文Token
    temperature: float                # 生成温度
    model: str                        # 使用的模型
    enable_rag: bool                  # 是否启用RAG
    enable_external_api: bool         # 是否启用外部API
    human_transfer_threshold: float   # 转人工阈值

# 默认配置
DEFAULT_CONFIG = ConversationConfig(
    max_turns=20,
    max_context_tokens=4000,
    temperature=0.7,
    model="deepseek-chat",
    enable_rag=True,
    enable_external_api=True,
    human_transfer_threshold=0.3
)
```

---

#### C1.2 LangGraph节点实现

**文件**: `backend/services/graph/nodes.py` (新建)

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from backend.services.intent_service import IntentService
from backend.services.rag_service import RAGService
from backend.services.llm_service import LLMService
from backend.services.external_api_service import ExternalAPIService

class ConversationNodes:
    """对话节点集合"""

    def __init__(
        self,
        intent_service: IntentService,
        rag_service: RAGService,
        llm_service: LLMService,
        external_api_service: ExternalAPIService,
        content_filter
    ):
        self.intent_service = intent_service
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.external_api_service = external_api_service
        self.content_filter = content_filter

    async def intent_recognition(self, state: ConversationState) -> dict:
        """
        意图识别节点

        输入: user_input
        输出: intent, intent_confidence, entities
        """
        user_input = state["user_input"]
        context = self._get_recent_context(state["messages"], n=3)

        # 调用意图识别服务
        result = await self.intent_service.classify_with_entities(
            text=user_input,
            context=context
        )

        return {
            "intent": IntentType(result["intent"]),
            "intent_confidence": result["confidence"],
            "entities": result["entities"],
            "current_node": "intent_recognition"
        }

    async def knowledge_retrieval(self, state: ConversationState) -> dict:
        """
        知识检索节点

        输入: user_input, intent, entities, tenant_id
        输出: retrieved_documents, retrieval_scores
        """
        # 构建检索查询
        query = self._build_retrieval_query(
            user_input=state["user_input"],
            intent=state["intent"],
            entities=state["entities"]
        )

        # 执行向量检索
        results = await self.rag_service.retrieve(
            tenant_id=state["tenant_id"],
            query=query,
            top_k=5,
            filter_by_intent=state["intent"].value if state["intent"] else None
        )

        return {
            "retrieved_documents": [r["document"] for r in results],
            "retrieval_scores": [r["score"] for r in results],
            "current_node": "knowledge_retrieval"
        }

    async def external_data_fetch(self, state: ConversationState) -> dict:
        """
        外部数据获取节点

        根据意图调用不同的外部API:
        - 订单查询: 调用订单系统
        - 物流查询: 调用物流API
        - 商品咨询: 调用商品系统
        """
        intent = state["intent"]
        entities = state["entities"]
        tenant_id = state["tenant_id"]

        external_data = {}

        if intent == IntentType.ORDER_QUERY and "order_id" in entities:
            order_data = await self.external_api_service.get_order(
                tenant_id=tenant_id,
                order_id=entities["order_id"]
            )
            external_data["order"] = order_data

        elif intent == IntentType.LOGISTICS_QUERY and "order_id" in entities:
            logistics_data = await self.external_api_service.get_logistics(
                tenant_id=tenant_id,
                order_id=entities["order_id"]
            )
            external_data["logistics"] = logistics_data

        elif intent == IntentType.PRODUCT_CONSULT and "product_id" in entities:
            product_data = await self.external_api_service.get_product(
                tenant_id=tenant_id,
                product_id=entities["product_id"]
            )
            external_data["product"] = product_data

        return {
            "external_data": external_data,
            "current_node": "external_data_fetch"
        }

    async def response_generation(self, state: ConversationState) -> dict:
        """
        响应生成节点

        输入: messages, retrieved_documents, external_data, intent
        输出: response, response_sources, tokens_used
        """
        # 构建系统提示
        system_prompt = self._build_system_prompt(
            intent=state["intent"],
            tenant_id=state["tenant_id"]
        )

        # 构建上下文
        context = self._build_generation_context(
            documents=state.get("retrieved_documents", []),
            external_data=state.get("external_data", {}),
            intent=state["intent"]
        )

        # 构建消息
        messages = [
            SystemMessage(content=system_prompt),
            *self._format_history(state["messages"]),
            HumanMessage(content=self._build_user_prompt(
                user_input=state["user_input"],
                context=context
            ))
        ]

        # 调用LLM生成
        response, usage = await self.llm_service.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # 安全过滤
        safe_response = await self.content_filter.filter(response)

        # 提取引用来源
        sources = self._extract_sources(
            state.get("retrieved_documents", []),
            state.get("external_data", {})
        )

        # 更新Token使用
        tokens_used = state.get("tokens_used", {"input": 0, "output": 0})
        tokens_used["input"] += usage.get("input_tokens", 0)
        tokens_used["output"] += usage.get("output_tokens", 0)

        return {
            "response": safe_response,
            "response_sources": sources,
            "tokens_used": tokens_used,
            "messages": [AIMessage(content=safe_response)],
            "current_node": "response_generation"
        }

    async def human_transfer_check(self, state: ConversationState) -> dict:
        """
        转人工检查节点

        判断是否需要转人工:
        - 用户明确要求
        - 意图置信度低
        - 多次无法解决
        - 投诉类意图
        """
        requires_human = False
        reason = None

        # 1. 用户明确要求
        if state["intent"] == IntentType.HUMAN_TRANSFER:
            requires_human = True
            reason = "user_request"

        # 2. 意图置信度低
        elif state["intent_confidence"] < 0.5:
            requires_human = True
            reason = "low_confidence"

        # 3. 投诉类意图
        elif state["intent"] == IntentType.COMPLAINT:
            requires_human = True
            reason = "complaint"

        # 4. 多轮未解决
        elif state["turn_count"] >= 5:
            # 检查用户满意度信号
            if self._detect_frustration(state["messages"]):
                requires_human = True
                reason = "user_frustration"

        return {
            "requires_human": requires_human,
            "current_node": "human_transfer_check"
        }

    def _build_system_prompt(self, intent: IntentType, tenant_id: str) -> str:
        """构建系统提示"""
        base_prompt = """你是一个专业的电商客服助手。请遵循以下原则:
1. 友好、专业、耐心地回答用户问题
2. 基于提供的知识库和数据回答，不要编造信息
3. 如果无法确定答案，诚实告知用户
4. 保护用户隐私，不泄露敏感信息
5. 回答简洁明了，避免冗长"""

        intent_prompts = {
            IntentType.ORDER_QUERY: "\n\n当前用户在查询订单，请根据订单数据准确回答。",
            IntentType.PRODUCT_CONSULT: "\n\n当前用户在咨询商品，请详细介绍商品信息。",
            IntentType.AFTER_SALES: "\n\n当前用户有售后需求，请耐心处理并提供解决方案。",
            IntentType.LOGISTICS_QUERY: "\n\n当前用户在查询物流，请提供准确的物流信息。",
            IntentType.COMPLAINT: "\n\n当前用户在投诉，请表示歉意并积极解决问题。",
        }

        return base_prompt + intent_prompts.get(intent, "")

    def _build_generation_context(
        self,
        documents: List[dict],
        external_data: dict,
        intent: IntentType
    ) -> str:
        """构建生成上下文"""
        context_parts = []

        # 知识库内容
        if documents:
            doc_content = "\n".join([
                f"- {doc.get('content', '')}"
                for doc in documents[:3]
            ])
            context_parts.append(f"【相关知识】\n{doc_content}")

        # 外部数据
        if "order" in external_data:
            order = external_data["order"]
            context_parts.append(f"""【订单信息】
订单号: {order.get('order_id')}
状态: {order.get('status')}
商品: {order.get('items')}
金额: {order.get('total_amount')}
下单时间: {order.get('created_at')}""")

        if "logistics" in external_data:
            logistics = external_data["logistics"]
            context_parts.append(f"""【物流信息】
物流公司: {logistics.get('carrier')}
运单号: {logistics.get('tracking_number')}
当前状态: {logistics.get('status')}
最新位置: {logistics.get('current_location')}""")

        if "product" in external_data:
            product = external_data["product"]
            context_parts.append(f"""【商品信息】
商品名称: {product.get('name')}
价格: {product.get('price')}
库存: {product.get('stock')}
描述: {product.get('description')}""")

        return "\n\n".join(context_parts) if context_parts else "无额外上下文"

    def _get_recent_context(self, messages: List[BaseMessage], n: int = 3) -> str:
        """获取最近n轮对话作为上下文"""
        recent = messages[-(n*2):] if len(messages) > n*2 else messages
        return "\n".join([
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content}"
            for m in recent
        ])

    def _detect_frustration(self, messages: List[BaseMessage]) -> bool:
        """检测用户是否有挫败感"""
        frustration_keywords = ["没用", "不行", "解决不了", "找人工", "投诉", "差评"]
        recent_user_messages = [
            m.content for m in messages[-4:]
            if isinstance(m, HumanMessage)
        ]
        return any(
            keyword in msg
            for msg in recent_user_messages
            for keyword in frustration_keywords
        )
```

---

#### C1.3 LangGraph边定义

**文件**: `backend/services/graph/edges.py` (新建)

```python
from typing import Literal
from backend.services.graph.state import ConversationState, IntentType

def route_after_intent(state: ConversationState) -> Literal[
    "knowledge_retrieval",
    "external_data_fetch",
    "human_transfer_check",
    "response_generation"
]:
    """
    意图识别后的路由决策

    根据意图类型决定下一步:
    - 需要外部数据的意图 → external_data_fetch
    - 需要知识检索的意图 → knowledge_retrieval
    - 转人工意图 → human_transfer_check
    - 其他 → response_generation
    """
    intent = state.get("intent")

    # 转人工直接跳转
    if intent == IntentType.HUMAN_TRANSFER:
        return "human_transfer_check"

    # 需要外部API的意图
    external_data_intents = [
        IntentType.ORDER_QUERY,
        IntentType.LOGISTICS_QUERY,
    ]

    if intent in external_data_intents and state.get("entities"):
        return "external_data_fetch"

    # 需要知识检索的意图
    knowledge_intents = [
        IntentType.PRODUCT_CONSULT,
        IntentType.AFTER_SALES,
        IntentType.PAYMENT_ISSUE,
        IntentType.PROMOTION,
        IntentType.ACCOUNT_ISSUE,
        IntentType.GENERAL,
    ]

    if intent in knowledge_intents:
        return "knowledge_retrieval"

    return "response_generation"

def route_after_external_data(state: ConversationState) -> Literal[
    "knowledge_retrieval",
    "response_generation"
]:
    """
    获取外部数据后的路由

    如果外部数据不足,补充知识检索
    """
    external_data = state.get("external_data", {})

    # 如果没有获取到数据,尝试知识检索
    if not external_data:
        return "knowledge_retrieval"

    return "response_generation"

def route_after_retrieval(state: ConversationState) -> Literal[
    "response_generation",
    "human_transfer_check"
]:
    """
    知识检索后的路由

    如果检索结果相关性太低,考虑转人工
    """
    scores = state.get("retrieval_scores", [])

    # 如果最高相关性分数低于阈值
    if scores and max(scores) < 0.5:
        # 检查是否已经多轮
        if state.get("turn_count", 0) >= 3:
            return "human_transfer_check"

    return "response_generation"

def should_continue(state: ConversationState) -> Literal["continue", "end"]:
    """
    判断对话是否继续

    结束条件:
    - 需要转人工
    - 发生错误
    - 用户结束对话
    """
    if state.get("requires_human"):
        return "end"

    if state.get("error"):
        return "end"

    return "continue"
```

---

#### C1.4 对话图编排

**文件**: `backend/services/graph/workflow.py` (新建)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.services.graph.state import ConversationState, DEFAULT_CONFIG
from backend.services.graph.nodes import ConversationNodes
from backend.services.graph.edges import (
    route_after_intent,
    route_after_external_data,
    route_after_retrieval,
    should_continue
)

class ConversationWorkflow:
    """对话工作流"""

    def __init__(
        self,
        nodes: ConversationNodes,
        checkpointer=None
    ):
        self.nodes = nodes
        self.checkpointer = checkpointer or SqliteSaver.from_conn_string(":memory:")
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建对话图"""

        # 创建图
        graph = StateGraph(ConversationState)

        # 添加节点
        graph.add_node("intent_recognition", self.nodes.intent_recognition)
        graph.add_node("knowledge_retrieval", self.nodes.knowledge_retrieval)
        graph.add_node("external_data_fetch", self.nodes.external_data_fetch)
        graph.add_node("response_generation", self.nodes.response_generation)
        graph.add_node("human_transfer_check", self.nodes.human_transfer_check)

        # 设置入口
        graph.set_entry_point("intent_recognition")

        # 添加条件边
        graph.add_conditional_edges(
            "intent_recognition",
            route_after_intent,
            {
                "knowledge_retrieval": "knowledge_retrieval",
                "external_data_fetch": "external_data_fetch",
                "human_transfer_check": "human_transfer_check",
                "response_generation": "response_generation"
            }
        )

        graph.add_conditional_edges(
            "external_data_fetch",
            route_after_external_data,
            {
                "knowledge_retrieval": "knowledge_retrieval",
                "response_generation": "response_generation"
            }
        )

        graph.add_conditional_edges(
            "knowledge_retrieval",
            route_after_retrieval,
            {
                "response_generation": "response_generation",
                "human_transfer_check": "human_transfer_check"
            }
        )

        # 响应生成后结束
        graph.add_edge("response_generation", END)

        # 人工检查后结束
        graph.add_edge("human_transfer_check", END)

        return graph.compile(checkpointer=self.checkpointer)

    async def run(
        self,
        tenant_id: str,
        conversation_id: str,
        customer_id: str,
        user_input: str,
        messages: list = None,
        config: dict = None
    ) -> ConversationState:
        """
        运行对话工作流

        Args:
            tenant_id: 租户ID
            conversation_id: 会话ID
            customer_id: 客户ID
            user_input: 用户输入
            messages: 历史消息
            config: 配置覆盖

        Returns:
            最终状态
        """
        from datetime import datetime
        from langchain_core.messages import HumanMessage

        # 初始化状态
        initial_state = ConversationState(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            messages=messages or [],
            user_input=user_input,
            intent=None,
            intent_confidence=0.0,
            entities={},
            retrieved_documents=[],
            retrieval_scores=[],
            external_data={},
            response="",
            response_sources=[],
            current_node="",
            requires_human=False,
            error=None,
            turn_count=len(messages) // 2 if messages else 0,
            started_at=datetime.utcnow(),
            tokens_used={"input": 0, "output": 0}
        )

        # 添加用户消息
        initial_state["messages"].append(HumanMessage(content=user_input))

        # 运行图
        thread_config = {
            "configurable": {
                "thread_id": conversation_id
            }
        }

        final_state = await self.graph.ainvoke(
            initial_state,
            config=thread_config
        )

        return final_state

    async def stream(
        self,
        tenant_id: str,
        conversation_id: str,
        customer_id: str,
        user_input: str,
        messages: list = None
    ):
        """
        流式运行对话工作流

        Yields:
            (node_name, state_update) 元组
        """
        from datetime import datetime
        from langchain_core.messages import HumanMessage

        initial_state = ConversationState(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            messages=messages or [],
            user_input=user_input,
            intent=None,
            intent_confidence=0.0,
            entities={},
            retrieved_documents=[],
            retrieval_scores=[],
            external_data={},
            response="",
            response_sources=[],
            current_node="",
            requires_human=False,
            error=None,
            turn_count=len(messages) // 2 if messages else 0,
            started_at=datetime.utcnow(),
            tokens_used={"input": 0, "output": 0}
        )

        initial_state["messages"].append(HumanMessage(content=user_input))

        thread_config = {
            "configurable": {
                "thread_id": conversation_id
            }
        }

        async for event in self.graph.astream(
            initial_state,
            config=thread_config
        ):
            yield event

class ConversationService:
    """对话服务(API层调用)"""

    def __init__(self, workflow: ConversationWorkflow, quota_service, db):
        self.workflow = workflow
        self.quota_service = quota_service
        self.db = db

    async def chat(
        self,
        tenant_id: str,
        conversation_id: str,
        customer_id: str,
        message: str
    ) -> dict:
        """
        处理聊天请求

        Returns:
            {
                "response": "...",
                "intent": "order_query",
                "requires_human": false,
                "sources": [...],
                "tokens_used": {...}
            }
        """
        # 获取历史消息
        conversation = await self._get_conversation(conversation_id)
        messages = conversation.messages if conversation else []

        # 运行工作流
        result = await self.workflow.run(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            user_input=message,
            messages=messages
        )

        # 保存消息
        await self._save_messages(conversation_id, message, result["response"])

        # 记录Token使用
        await self._record_token_usage(tenant_id, result["tokens_used"])

        # 触发事件
        await self._publish_events(tenant_id, conversation_id, result)

        return {
            "response": result["response"],
            "intent": result["intent"].value if result["intent"] else None,
            "requires_human": result["requires_human"],
            "sources": result["response_sources"],
            "tokens_used": result["tokens_used"]
        }
```

---

#### C1.5 上下文滑动窗口

**文件**: `backend/services/memory_service.py` (重构)

```python
from typing import List, Tuple
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import tiktoken

class ContextWindowManager:
    """上下文窗口管理器"""

    def __init__(
        self,
        max_tokens: int = 4000,
        reserve_for_response: int = 1000,
        model: str = "gpt-3.5-turbo"
    ):
        self.max_tokens = max_tokens
        self.reserve_for_response = reserve_for_response
        self.available_tokens = max_tokens - reserve_for_response

        # Token计数器
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """计算文本Token数"""
        return len(self.tokenizer.encode(text))

    def count_message_tokens(self, message: BaseMessage) -> int:
        """计算消息Token数"""
        # 消息格式开销约4 tokens
        return self.count_tokens(message.content) + 4

    def count_messages_tokens(self, messages: List[BaseMessage]) -> int:
        """计算消息列表总Token数"""
        return sum(self.count_message_tokens(m) for m in messages)

    def trim_messages(
        self,
        messages: List[BaseMessage],
        system_message: BaseMessage = None
    ) -> List[BaseMessage]:
        """
        裁剪消息以适应上下文窗口

        策略:
        1. 始终保留system message
        2. 保留最近的消息
        3. 如果还是超限,进行摘要压缩
        """
        result = []
        current_tokens = 0

        # 预留system message的token
        if system_message:
            system_tokens = self.count_message_tokens(system_message)
            current_tokens += system_tokens

        # 从最新消息开始添加
        for message in reversed(messages):
            msg_tokens = self.count_message_tokens(message)

            if current_tokens + msg_tokens <= self.available_tokens:
                result.insert(0, message)
                current_tokens += msg_tokens
            else:
                # 超限,停止添加
                break

        # 如果结果为空(单条消息就超限),进行截断
        if not result and messages:
            last_message = messages[-1]
            truncated_content = self._truncate_content(
                last_message.content,
                self.available_tokens - current_tokens - 100  # 留一些余量
            )
            result = [type(last_message)(content=truncated_content)]

        return result

    def summarize_context(
        self,
        messages: List[BaseMessage],
        llm_service
    ) -> Tuple[str, List[BaseMessage]]:
        """
        摘要压缩上下文

        Returns:
            (摘要, 保留的最近消息)
        """
        if len(messages) <= 4:
            return None, messages

        # 分割: 早期消息用于摘要,保留最近2轮
        messages_to_summarize = messages[:-4]
        messages_to_keep = messages[-4:]

        # 生成摘要
        summary_prompt = """请将以下对话历史压缩成简洁的摘要,保留关键信息:

{conversation}

摘要:"""

        conversation_text = "\n".join([
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content}"
            for m in messages_to_summarize
        ])

        summary = llm_service.generate_sync(
            summary_prompt.format(conversation=conversation_text),
            max_tokens=200
        )

        return summary, messages_to_keep

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """截断内容到指定Token数"""
        tokens = self.tokenizer.encode(content)
        if len(tokens) <= max_tokens:
            return content

        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens) + "..."

class ConversationMemory:
    """对话记忆管理"""

    def __init__(
        self,
        redis,
        window_manager: ContextWindowManager
    ):
        self.redis = redis
        self.window_manager = window_manager

    async def get_messages(
        self,
        conversation_id: str,
        max_messages: int = 20
    ) -> List[BaseMessage]:
        """获取对话消息历史"""
        key = f"conversation:{conversation_id}:messages"
        raw_messages = await self.redis.lrange(key, -max_messages, -1)

        messages = []
        for raw in raw_messages:
            data = json.loads(raw)
            if data["role"] == "user":
                messages.append(HumanMessage(content=data["content"]))
            else:
                messages.append(AIMessage(content=data["content"]))

        return messages

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ):
        """添加消息"""
        key = f"conversation:{conversation_id}:messages"
        message_data = json.dumps({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        await self.redis.rpush(key, message_data)
        await self.redis.expire(key, 86400 * 7)  # 7天过期

    async def get_context_for_generation(
        self,
        conversation_id: str,
        system_message: str = None
    ) -> List[BaseMessage]:
        """获取用于生成的上下文(已裁剪)"""
        messages = await self.get_messages(conversation_id)

        system_msg = SystemMessage(content=system_message) if system_message else None

        return self.window_manager.trim_messages(messages, system_msg)

    async def clear(self, conversation_id: str):
        """清除对话记忆"""
        key = f"conversation:{conversation_id}:messages"
        await self.redis.delete(key)
```

---

### 2.3 接口契约

#### 对外提供的接口

| 接口 | 类型 | 说明 | 使用方 |
|------|------|------|--------|
| `ConversationService.chat()` | 方法 | 处理聊天 | API Router |
| `ConversationWorkflow.stream()` | 方法 | 流式对话 | WebSocket |

#### API端点

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/conversation/chat` | 同步 | 发送消息获取回复 |
| `WS /api/v1/ws/chat` | WebSocket | 流式对话 |

---

## 三、第二阶段：RAG系统完善 (Week 3-5)

### 3.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| C2.1 | Milvus分区策略 | P0 | 1.5天 | 待开始 |
| C2.2 | 完整RAG流程 | P0 | 2天 | 待开始 |
| C2.3 | Rerank集成 | P1 | 1.5天 | 待开始 |
| C2.4 | RAG用量记录 | P1 | 1天 | 待开始 |
| C2.5 | 向量更新任务 | P1 | 1.5天 | 待开始 |
| C2.6 | 权限验证集成 | P0 | 1天 | 待开始 |

### 3.2 详细设计

#### C2.1 Milvus分区策略

**文件**: `backend/services/milvus_service.py` (重构)

```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

class MilvusService:
    """Milvus向量数据库服务"""

    COLLECTION_NAME = "knowledge_vectors"
    DIMENSION = 1536  # OpenAI embedding维度

    def __init__(self, config: MilvusConfig):
        self.host = config.host
        self.port = config.port
        self._connect()
        self._ensure_collection()

    def _connect(self):
        """连接Milvus"""
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port
        )

    def _ensure_collection(self):
        """确保集合存在"""
        if utility.has_collection(self.COLLECTION_NAME):
            self.collection = Collection(self.COLLECTION_NAME)
            return

        # 创建集合Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="knowledge_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.DIMENSION),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]

        schema = CollectionSchema(fields=fields, description="Knowledge base vectors")
        self.collection = Collection(self.COLLECTION_NAME, schema)

        # 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256}
        }
        self.collection.create_index("vector", index_params)

        # 创建标量索引(用于分区过滤)
        self.collection.create_index("tenant_id", {"index_type": "Trie"})

    async def insert(
        self,
        tenant_id: str,
        knowledge_id: str,
        chunks: List[dict]
    ):
        """
        插入向量

        Args:
            tenant_id: 租户ID
            knowledge_id: 知识ID
            chunks: [{"content": "...", "vector": [...], "category": "..."}]
        """
        import uuid
        from datetime import datetime

        data = []
        for i, chunk in enumerate(chunks):
            data.append({
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "knowledge_id": knowledge_id,
                "chunk_index": i,
                "content": chunk["content"],
                "category": chunk.get("category", "general"),
                "vector": chunk["vector"],
                "created_at": int(datetime.utcnow().timestamp())
            })

        self.collection.insert(data)
        self.collection.flush()

    async def search(
        self,
        tenant_id: str,
        query_vector: List[float],
        top_k: int = 5,
        category_filter: str = None,
        score_threshold: float = 0.5
    ) -> List[dict]:
        """
        搜索向量

        Args:
            tenant_id: 租户ID (必须,实现租户隔离)
            query_vector: 查询向量
            top_k: 返回数量
            category_filter: 类别过滤
            score_threshold: 分数阈值

        Returns:
            [{"id": "...", "content": "...", "score": 0.85, ...}]
        """
        self.collection.load()

        # 构建过滤表达式 (租户隔离)
        filter_expr = f'tenant_id == "{tenant_id}"'
        if category_filter:
            filter_expr += f' and category == "{category_filter}"'

        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 128}
        }

        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["content", "knowledge_id", "category", "chunk_index"]
        )

        # 格式化结果
        formatted = []
        for hits in results:
            for hit in hits:
                score = hit.score  # COSINE相似度,越大越好
                if score >= score_threshold:
                    formatted.append({
                        "id": hit.id,
                        "content": hit.entity.get("content"),
                        "knowledge_id": hit.entity.get("knowledge_id"),
                        "category": hit.entity.get("category"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "score": score
                    })

        return formatted

    async def delete_by_knowledge(self, tenant_id: str, knowledge_id: str):
        """删除知识的所有向量"""
        expr = f'tenant_id == "{tenant_id}" and knowledge_id == "{knowledge_id}"'
        self.collection.delete(expr)

    async def delete_by_tenant(self, tenant_id: str):
        """删除租户的所有向量"""
        expr = f'tenant_id == "{tenant_id}"'
        self.collection.delete(expr)

    async def get_tenant_stats(self, tenant_id: str) -> dict:
        """获取租户向量统计"""
        expr = f'tenant_id == "{tenant_id}"'
        # 注意: Milvus不支持直接count,需要通过查询
        results = self.collection.query(
            expr=expr,
            output_fields=["knowledge_id"],
            limit=100000
        )

        knowledge_ids = set(r["knowledge_id"] for r in results)

        return {
            "vector_count": len(results),
            "knowledge_count": len(knowledge_ids)
        }
```

---

#### C2.3 Rerank集成

**文件**: `backend/services/rerank_service.py` (新建)

```python
from typing import List
import httpx

class RerankService:
    """重排序服务"""

    def __init__(self, config):
        self.api_key = config.RERANK_API_KEY
        self.model = config.RERANK_MODEL or "bge-reranker-large"
        self.api_url = config.RERANK_API_URL

    async def rerank(
        self,
        query: str,
        documents: List[dict],
        top_k: int = 5
    ) -> List[dict]:
        """
        对检索结果重排序

        Args:
            query: 查询文本
            documents: 检索到的文档 [{"content": "...", "score": 0.8, ...}]
            top_k: 返回数量

        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []

        # 如果文档数少于等于top_k,直接返回
        if len(documents) <= top_k:
            return documents

        # 调用Rerank API
        try:
            scores = await self._call_rerank_api(
                query=query,
                passages=[doc["content"] for doc in documents]
            )

            # 合并分数
            for i, doc in enumerate(documents):
                doc["rerank_score"] = scores[i]

            # 按rerank分数排序
            sorted_docs = sorted(
                documents,
                key=lambda x: x["rerank_score"],
                reverse=True
            )

            return sorted_docs[:top_k]

        except Exception as e:
            # Rerank失败,降级到原始排序
            logger.warning(f"Rerank failed: {e}, fallback to original order")
            return documents[:top_k]

    async def _call_rerank_api(
        self,
        query: str,
        passages: List[str]
    ) -> List[float]:
        """调用Rerank API"""

        # 使用本地模型(BGE-Reranker)
        if self.api_url.startswith("http://localhost"):
            return await self._call_local_reranker(query, passages)

        # 使用Cohere Rerank API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/rerank",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "query": query,
                    "documents": passages,
                    "return_documents": False
                }
            )
            response.raise_for_status()

            data = response.json()
            # 按原始索引排序分数
            scores = [0.0] * len(passages)
            for result in data["results"]:
                scores[result["index"]] = result["relevance_score"]

            return scores

    async def _call_local_reranker(
        self,
        query: str,
        passages: List[str]
    ) -> List[float]:
        """调用本地Reranker服务"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/rerank",
                json={
                    "query": query,
                    "passages": passages
                }
            )
            response.raise_for_status()
            return response.json()["scores"]
```

---

## 四、第三阶段：多模型支持 (Week 7-9)

### 4.1 任务清单

| ID | 任务 | 优先级 | 工作量 | 状态 |
|----|------|--------|--------|------|
| C3.1 | 多LLM适配器 | P0 | 3天 | 待开始 |
| C3.2 | 模型路由器 | P0 | 2天 | 待开始 |
| C3.3 | 租户模型配置 | P1 | 1天 | 待开始 |
| C3.4 | 负载均衡 | P1 | 1.5天 | 待开始 |
| C3.5 | 故障转移 | P1 | 1.5天 | 待开始 |

### 4.2 详细设计

#### C3.1 多LLM适配器

**文件**: `backend/services/llm/adapters/base.py` (新建)

```python
from abc import ABC, abstractmethod
from typing import List, Tuple, AsyncIterator
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: dict  # {"input_tokens": 0, "output_tokens": 0}
    finish_reason: str

@dataclass
class LLMConfig:
    """LLM配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

class LLMAdapter(ABC):
    """LLM适配器基类"""

    @property
    @abstractmethod
    def provider(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[dict],
        config: LLMConfig
    ) -> LLMResponse:
        """生成回复"""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[dict],
        config: LLMConfig
    ) -> AsyncIterator[str]:
        """流式生成"""
        pass

    @abstractmethod
    def count_tokens(self, text: str, model: str = None) -> int:
        """计算Token数"""
        pass

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.generate(
                messages=[{"role": "user", "content": "hi"}],
                config=LLMConfig(model=self.supported_models[0], max_tokens=5)
            )
            return bool(response.content)
        except:
            return False
```

**文件**: `backend/services/llm/adapters/openai_adapter.py`

```python
from openai import AsyncOpenAI
import tiktoken

class OpenAIAdapter(LLMAdapter):
    """OpenAI适配器"""

    def __init__(self, api_key: str, base_url: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def generate(
        self,
        messages: List[dict],
        config: LLMConfig
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    async def stream_generate(
        self,
        messages: List[dict],
        config: LLMConfig
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str, model: str = None) -> int:
        model = model or "gpt-3.5-turbo"
        try:
            encoding = tiktoken.encoding_for_model(model)
        except:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
```

**文件**: `backend/services/llm/adapters/deepseek_adapter.py`

```python
class DeepSeekAdapter(LLMAdapter):
    """DeepSeek适配器(OpenAI兼容)"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

    @property
    def provider(self) -> str:
        return "deepseek"

    @property
    def supported_models(self) -> List[str]:
        return ["deepseek-chat", "deepseek-coder"]

    # generate和stream_generate与OpenAI相同...
```

---

#### C3.2 模型路由器

**文件**: `backend/services/llm/router.py` (新建)

```python
from typing import Optional
from backend.services.llm.adapters.base import LLMAdapter, LLMConfig, LLMResponse

class ModelRouter:
    """
    模型路由器

    职责:
    1. 根据租户配置选择模型
    2. 根据意图路由到合适模型
    3. 负载均衡
    4. 故障转移
    """

    # 意图-模型映射
    INTENT_MODEL_MAPPING = {
        "order_query": "deepseek-chat",      # 简单查询用轻量模型
        "product_consult": "gpt-4o-mini",    # 商品咨询
        "after_sales": "gpt-4o",             # 售后需要更好理解
        "complaint": "gpt-4o",               # 投诉需要高情商
        "general": "deepseek-chat",
    }

    def __init__(
        self,
        adapters: dict[str, LLMAdapter],
        default_model: str = "deepseek-chat"
    ):
        self.adapters = adapters  # {"openai": adapter, "deepseek": adapter}
        self.default_model = default_model
        self.model_health: dict[str, bool] = {}

    async def route(
        self,
        tenant_id: str,
        intent: str = None,
        preferred_model: str = None
    ) -> tuple[LLMAdapter, str]:
        """
        路由到合适的模型

        Returns:
            (adapter, model_name)
        """
        # 1. 优先使用指定模型
        if preferred_model:
            adapter = self._get_adapter_for_model(preferred_model)
            if adapter and await self._check_health(preferred_model):
                return adapter, preferred_model

        # 2. 检查租户配置
        tenant_model = await self._get_tenant_preferred_model(tenant_id)
        if tenant_model:
            adapter = self._get_adapter_for_model(tenant_model)
            if adapter and await self._check_health(tenant_model):
                return adapter, tenant_model

        # 3. 根据意图路由
        if intent and intent in self.INTENT_MODEL_MAPPING:
            model = self.INTENT_MODEL_MAPPING[intent]
            adapter = self._get_adapter_for_model(model)
            if adapter and await self._check_health(model):
                return adapter, model

        # 4. 使用默认模型
        adapter = self._get_adapter_for_model(self.default_model)
        if adapter and await self._check_health(self.default_model):
            return adapter, self.default_model

        # 5. 故障转移: 找任何可用模型
        return await self._fallback_to_any_available()

    async def generate_with_fallback(
        self,
        messages: List[dict],
        config: LLMConfig,
        tenant_id: str = None,
        intent: str = None
    ) -> LLMResponse:
        """
        带故障转移的生成

        如果主模型失败,自动切换备选模型
        """
        adapter, model = await self.route(tenant_id, intent, config.model)
        config.model = model

        try:
            return await adapter.generate(messages, config)
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}, trying fallback")

            # 标记不健康
            self.model_health[model] = False

            # 尝试其他模型
            for fallback_model in self._get_fallback_models(model):
                fallback_adapter = self._get_adapter_for_model(fallback_model)
                if fallback_adapter:
                    try:
                        config.model = fallback_model
                        return await fallback_adapter.generate(messages, config)
                    except:
                        continue

            raise Exception("All models failed")

    def _get_adapter_for_model(self, model: str) -> Optional[LLMAdapter]:
        """根据模型名获取适配器"""
        model_provider_map = {
            "gpt-4o": "openai",
            "gpt-4o-mini": "openai",
            "gpt-4-turbo": "openai",
            "gpt-3.5-turbo": "openai",
            "deepseek-chat": "deepseek",
            "deepseek-coder": "deepseek",
            "claude-3-opus": "anthropic",
            "claude-3-sonnet": "anthropic",
        }

        provider = model_provider_map.get(model)
        return self.adapters.get(provider)

    async def _check_health(self, model: str) -> bool:
        """检查模型健康状态"""
        # 使用缓存的健康状态
        if model in self.model_health:
            return self.model_health[model]

        adapter = self._get_adapter_for_model(model)
        if not adapter:
            return False

        healthy = await adapter.health_check()
        self.model_health[model] = healthy
        return healthy

    def _get_fallback_models(self, failed_model: str) -> List[str]:
        """获取备选模型列表"""
        all_models = ["deepseek-chat", "gpt-4o-mini", "gpt-4o"]
        return [m for m in all_models if m != failed_model]

    async def _fallback_to_any_available(self) -> tuple[LLMAdapter, str]:
        """降级到任何可用模型"""
        for provider, adapter in self.adapters.items():
            for model in adapter.supported_models:
                if await self._check_health(model):
                    return adapter, model

        raise Exception("No available LLM model")

    async def _get_tenant_preferred_model(self, tenant_id: str) -> Optional[str]:
        """获取租户偏好模型"""
        # 从缓存或数据库获取
        # ...
        return None
```

---

## 五、验收标准

### 5.1 第一阶段验收 (Week 2末)

- [ ] LangGraph工作流正常运行
- [ ] 意图识别准确率 > 85%
- [ ] 对话上下文正确保持
- [ ] Token使用正确统计
- [ ] 转人工逻辑正确触发

### 5.2 第二阶段验收 (Week 5末)

- [ ] 不同租户数据完全隔离
- [ ] RAG检索相关性 > 0.7
- [ ] Rerank提升检索质量
- [ ] 向量更新任务正常执行

### 5.3 第三阶段验收 (Week 9末)

- [ ] 支持3种以上LLM
- [ ] 模型切换无感知
- [ ] 故障自动转移
- [ ] 负载分配合理

---

## 六、监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `conversation_latency_p95` | 对话响应P95延迟 | > 3s |
| `intent_accuracy` | 意图识别准确率 | < 80% |
| `rag_retrieval_score_avg` | RAG检索平均分 | < 0.6 |
| `llm_error_rate` | LLM调用错误率 | > 1% |
| `token_usage_daily` | 每日Token消耗 | 监控趋势 |

---

**文档维护者**: Line C负责人
**创建日期**: 2026-02-05
**版本**: v1.0