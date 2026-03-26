"""意图识别：关键词优先，未命中或冲突时调用 LLM 二次分类。"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage

from .constants import (
    INTENT_BUG_QUERY,
    INTENT_CPP_QUERY,
    INTENT_DESIGN_DOC,
    INTENT_POLICY_QUERY,
    INTENT_SMALLTALK,
    KEYWORD_WEIGHTS,
)

logger = logging.getLogger(__name__)

_VALID_LABELS = frozenset(
    {
        INTENT_DESIGN_DOC,
        INTENT_CPP_QUERY,
        INTENT_BUG_QUERY,
        INTENT_POLICY_QUERY,
        INTENT_SMALLTALK,
    }
)


def _score_keywords(text: str) -> dict[str, int]:
    lower = text.lower()
    scores: dict[str, int] = {k: 0 for k in KEYWORD_WEIGHTS}
    for intent, weights in KEYWORD_WEIGHTS.items():
        for word, w in weights.items():
            if word in lower or word in text:
                scores[intent] += w
    return scores


def _looks_like_cpp_code(text: str) -> bool:
    patterns = (
        r"\b(struct|enum|class|template|namespace|void|int|double|const)\b",
        r"::",
        r"#include",
        r"\.hpp\b",
        r"\.hxx\b",
        r"\.h\b",
    )
    return any(re.search(p, text, re.I) for p in patterns)


def classify_intent_keyword_only(user_message: str) -> str | None:
    """
    仅关键词打分。若唯一最高分明显则返回标签，否则返回 None（需 LLM 或兜底）。
    """
    msg = (user_message or "").strip()
    if not msg:
        return INTENT_SMALLTALK

    scores = _score_keywords(msg)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score <= 0:
        return None
    if best_score > second_score:
        return best_intent
    return None


def classify_intent_llm(user_message: str, llm: Any | None = None) -> str:
    """调用 LLM 从五类中选一类；失败时返回 smalltalk。"""
    try:
        from utils.my_llm import llm as default_llm
    except Exception as e:
        logger.warning("无法加载默认 LLM：%s", e)
        return INTENT_SMALLTALK

    model = llm or default_llm
    labels = ", ".join(sorted(_VALID_LABELS))
    prompt = (
        "你是意图分类器。根据用户问题，从下列标签中**只输出一个**英文标签，不要解释：\n"
        f"{labels}\n\n"
        "含义：design_doc=设计或培训资料；cpp_query=C++头文件/实现或API；"
        "bug_query=缺陷/Bug；policy_query=行政条例制度；smalltalk=闲聊或无法归类。\n\n"
        f"用户问题：{user_message.strip()}"
    )
    try:
        resp = model.invoke([HumanMessage(content=prompt)])
        raw = (getattr(resp, "content", None) or "").strip()
    except Exception as e:
        logger.warning("LLM 意图分类失败：%s", e)
        return INTENT_SMALLTALK

    token = raw.split()[0].strip().rstrip(".,;:")
    token = token.strip("`\"'")
    if token in _VALID_LABELS:
        return token
    for label in _VALID_LABELS:
        if label in raw:
            return label
    return INTENT_SMALLTALK


def classify_intent(user_message: str, *, llm: Any | None = None) -> str:
    """
    两阶段：关键词 ->（未命中或平局）LLM -> 仍模糊则 smalltalk；
    无 API 时平局若像代码则偏向 cpp_query。
    """
    msg = (user_message or "").strip()
    kw = classify_intent_keyword_only(msg)
    if kw is not None:
        return kw

    try:
        return classify_intent_llm(msg, llm=llm)
    except Exception:
        if _looks_like_cpp_code(msg):
            return INTENT_CPP_QUERY
        return INTENT_SMALLTALK
