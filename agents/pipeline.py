"""Agent 对外入口：编译并调用 LangGraph 对话图。"""

from __future__ import annotations

import logging
from typing import Any

from .graph import compile_chat_graph, invoke_chat_turn

logger = logging.getLogger(__name__)

# 避免每轮重复 compile（同一 memory + 同一 llm 对象复用已编译图）
_compiled_cache: dict[tuple[int, int], Any] = {}


def _compiled_for(memory: Any, llm: Any | None) -> Any:
    key = (id(memory), id(llm) if llm is not None else 0)
    if key not in _compiled_cache:
        _compiled_cache[key] = compile_chat_graph(memory=memory, llm=llm)
        logger.debug("已编译 LangGraph 对话图 cache_key=%s", key)
    return _compiled_cache[key]


def run_chat_turn(
    user_id: str,
    user_message: str,
    memory: Any,
    *,
    llm: Any | None = None,
) -> str:
    """
    单轮对话：经 LangGraph（normalize → 意图 → Cpp/非Cpp → 记忆）。

    空输入返回空字符串，不写入记忆。
    """
    compiled = _compiled_for(memory, llm)
    return invoke_chat_turn(compiled, user_id=user_id, user_message=user_message)
