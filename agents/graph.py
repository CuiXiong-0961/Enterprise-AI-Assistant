"""LangGraph 1.x 状态图：对齐 process.md 的 start → 意图 → 分支 → 记忆。"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from repository.chroma_crud import ChromaRepository
from repository.CppHeader import get_cpp_headers_collection
from repository.Develop import get_knowledge_docs_collection

from .constants import INTENT_CPP_QUERY, INTENT_DESIGN_DOC, INTENT_SMALLTALK, NOT_IMPLEMENTED_REPLY
from .cpp_answer import run_cpp_answer
from .intent import classify_intent
from .knowledge_answer import format_knowledge_answer, retrieve_knowledge_docs

logger = logging.getLogger(__name__)


class ChatGraphState(TypedDict, total=False):
    """单轮对话在图中的共享状态（可序列化字段，便于后续加 checkpoint）。"""

    user_id: str
    user_message: str
    intent: str
    assistant_text: str
    update_profile: bool
    """高置信 Cpp 回答为 True；低置信或错误为 False。"""
    done_empty: bool
    """用户未输入有效内容时为 True，跳过后续与记忆写入。"""


def _reply_non_cpp(intent: str) -> str:
    if intent == INTENT_SMALLTALK:
        return (
            "你好，我是企业 AI 助手。\n\n"
            "当前已接入 **C++ 头文件 / 实现相关检索**（向量库 `cpp_headers`）。"
            "请直接描述你要查的符号、类或接口；其他能力（设计资料、Bug、行政条例）将陆续开放。"
        )
    return NOT_IMPLEMENTED_REPLY


def build_chat_graph(*, memory: Any, llm: Any | None = None) -> StateGraph:
    """
    构建未编译的 StateGraph；调用方 ``.compile()`` 后 ``invoke``。

    ``memory`` 为 ``MemoryManager`` 实例，通过闭包注入各节点（不参与序列化）。
    """

    def node_normalize(state: ChatGraphState) -> dict[str, Any]:
        """入口：清洗输入；空输入则标记 done_empty，直接结束。"""
        raw = (state.get("user_message") or "").strip()
        if not raw:
            return {"user_message": "", "assistant_text": "", "done_empty": True}
        return {"user_message": raw, "done_empty": False}

    def route_after_normalize(state: ChatGraphState) -> Literal["classify_intent", "end"]:
        if state.get("done_empty"):
            return "end"
        return "classify_intent"

    def node_classify_intent(state: ChatGraphState) -> dict[str, Any]:
        """意图识别：关键词 + LLM。"""
        intent = classify_intent(state["user_message"], llm=llm)
        return {"intent": intent}

    def route_after_intent(state: ChatGraphState) -> Literal["cpp_path", "knowledge_path", "non_cpp_reply"]:
        intent = state.get("intent")
        if intent == INTENT_CPP_QUERY:
            return "cpp_path"
        if intent == INTENT_DESIGN_DOC:
            return "knowledge_path"
        return "non_cpp_reply"

    def node_non_cpp_reply(state: ChatGraphState) -> dict[str, Any]:
        """非 Cpp 意图：固定话术。"""
        reply = _reply_non_cpp(state.get("intent") or INTENT_SMALLTALK)
        return {"assistant_text": reply, "update_profile": True}

    def node_cpp_path(state: ChatGraphState) -> dict[str, Any]:
        """Cpp：Chroma 检索 + LLM 作答。"""
        text = state["user_message"]
        try:
            repo = ChromaRepository()
            coll = get_cpp_headers_collection(repo)
        except Exception as e:
            logger.exception("Chroma / cpp_headers 初始化失败：%s", e)
            reply = (
                "**检索暂不可用**（向量库连接或配置异常），请稍后重试或检查 `repository/chroma_db` 与依赖。\n"
                f"详情：{e!s}"
            )
            return {"assistant_text": reply, "update_profile": False}

        result = run_cpp_answer(text, coll, llm=llm)
        return {
            "assistant_text": result.assistant_text,
            "update_profile": result.update_profile,
        }

    def node_knowledge_path(state: ChatGraphState) -> dict[str, Any]:
        """设计/培训/开发资料：检索 knowledge_docs 并输出带来源的结果。"""
        text = state["user_message"]
        try:
            repo = ChromaRepository()
            coll = get_knowledge_docs_collection(repo)
        except Exception as e:
            logger.exception("Chroma / knowledge_docs 初始化失败：%s", e)
            reply = (
                "**检索暂不可用**（knowledge_docs 向量库连接或配置异常）。\n"
                f"详情：{e!s}"
            )
            return {"assistant_text": reply, "update_profile": False}

        hits = retrieve_knowledge_docs(coll, text, top_k=5)
        reply = format_knowledge_answer(text, hits)
        # 检索结果本身不更新画像（避免把低质量检索写成偏好）
        return {"assistant_text": reply, "update_profile": False}

    def node_memory_write(state: ChatGraphState) -> dict[str, Any]:
        """写入短时记忆；画像是否更新由 update_profile 控制。"""
        if state.get("done_empty"):
            return {}
        memory.record_turn(
            state["user_id"],
            state["user_message"],
            state.get("assistant_text") or "",
            intent=state.get("intent"),
            update_profile=bool(state.get("update_profile", True)),
        )
        return {}

    graph = StateGraph(ChatGraphState)
    graph.add_node("normalize", node_normalize)
    graph.add_node("classify_intent", node_classify_intent)
    graph.add_node("non_cpp_reply", node_non_cpp_reply)
    graph.add_node("cpp_path", node_cpp_path)
    graph.add_node("knowledge_path", node_knowledge_path)
    graph.add_node("memory_write", node_memory_write)

    graph.add_edge(START, "normalize")
    graph.add_conditional_edges(
        "normalize",
        route_after_normalize,
        {"classify_intent": "classify_intent", "end": END},
    )
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {"cpp_path": "cpp_path", "knowledge_path": "knowledge_path", "non_cpp_reply": "non_cpp_reply"},
    )
    graph.add_edge("non_cpp_reply", "memory_write")
    graph.add_edge("cpp_path", "memory_write")
    graph.add_edge("knowledge_path", "memory_write")
    graph.add_edge("memory_write", END)

    return graph


def compile_chat_graph(*, memory: Any, llm: Any | None = None) -> Any:
    """编译图，供多次 invoke。"""
    return build_chat_graph(memory=memory, llm=llm).compile()


def invoke_chat_turn(
    compiled: Any,
    *,
    user_id: str,
    user_message: str,
) -> str:
    """执行单轮，返回助手可见文本。"""
    out: ChatGraphState = compiled.invoke(
        {
            "user_id": user_id,
            "user_message": user_message,
        }
    )
    return (out.get("assistant_text") or "").strip()
