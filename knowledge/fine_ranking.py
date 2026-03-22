"""
线上检索 — 精排层：用大模型对「查询 + 融合结果」相关性打分，取 top-k。

默认使用 ``utils.my_llm`` 中的 ``llm``；可通过参数注入其它 LangChain ChatModel。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from .fusion import FusedDocument

logger = logging.getLogger(__name__)


@dataclass
class FineRankingParams:
    """精排超参数。"""

    top_k: int = 5
    """最终返回条数。"""
    max_docs_for_llm: int = 15
    """送入大模型的最大融合文档数（控制 token）。"""
    text_truncate: int = 1200
    """每条文档正文截断长度（字符）。"""
    temperature: float | None = 0.0
    """覆盖 LLM 温度；``None`` 表示沿用 ``llm`` 实例原有设置。"""


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```\w*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _parse_llm_ranking_json(raw: str) -> list[tuple[int, float]]:
    """解析 ``[{"index":0,"score":0.9}, ...]``，下标对应融合列表顺序。"""
    s = _strip_code_fence(raw)
    m = re.search(r"\[[\s\S]*\]", s)
    if not m:
        return []
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[tuple[int, float]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        sc = item.get("score")
        if isinstance(idx, int) and isinstance(sc, (int, float)):
            out.append((idx, float(sc)))
    return out


def _bind_temperature(llm: BaseChatModel, temperature: float | None) -> BaseChatModel:
    if temperature is None:
        return llm
    try:
        if hasattr(llm, "model_copy"):
            return llm.model_copy(update={"temperature": temperature})  # type: ignore[return-value]
    except Exception:
        logger.warning("无法覆盖 llm.temperature，使用原实例")
    return llm


def fine_rerank_llm(
    query: str,
    fused: list[FusedDocument],
    *,
    params: FineRankingParams | None = None,
    llm: BaseChatModel | None = None,
) -> list[FusedDocument]:
    """
    使用大模型对融合文档按相关性重排，返回 ``top_k`` 条。

    若 JSON 解析失败或调用异常，则回退为按 ``fused_score`` 排序后截取 ``top_k``。
    """
    p = params or FineRankingParams()
    if not fused:
        return []

    from utils.my_llm import llm as default_llm

    model = _bind_temperature(llm or default_llm, p.temperature)

    take = fused[: max(1, p.max_docs_for_llm)]
    lines: list[str] = []
    for i, doc in enumerate(take):
        body = (doc.text or "").replace("\r\n", "\n")[: p.text_truncate]
        lines.append(f"[{i}] id={doc.doc_id}\n{body}")

    user_prompt = (
        f"用户查询：{query}\n\n"
        "以下为候选文档，下标从 0 开始，与方括号中的数字一致：\n\n"
        + "\n\n---\n\n".join(lines)
        + "\n\n请仅输出一个 JSON 数组，元素格式为："
        '{"index": <整数下标>, "score": <0到1的浮点数>, "brief": "<不超过40字的相关性说明>"}。'
        "按 score 从高到低排序。不要输出数组以外的任何文字。"
    )

    try:
        resp = model.invoke([HumanMessage(content=user_prompt)])
        content = getattr(resp, "content", "") or ""
        ranked = _parse_llm_ranking_json(str(content))
    except Exception:
        logger.exception("精排 LLM 调用或解析失败，回退 fused_score 排序")
        ranked = []

    if not ranked:
        return sorted(fused, key=lambda d: d.fused_score, reverse=True)[: p.top_k]

    by_index = {i: take[i] for i in range(len(take))}
    seen: set[int] = set()
    ordered: list[FusedDocument] = []
    for idx, sc in ranked:
        if idx in seen or idx not in by_index:
            continue
        seen.add(idx)
        base = by_index[idx]
        ordered.append(
            FusedDocument(
                doc_id=base.doc_id,
                text=base.text,
                fused_score=sc,
                fusion_rank=len(ordered),
                sources=(base.sources + "|llm") if base.sources else "llm",
            )
        )
        if len(ordered) >= p.top_k:
            break

    if not ordered:
        return sorted(fused, key=lambda d: d.fused_score, reverse=True)[: p.top_k]

    if len(ordered) < p.top_k:
        for i in range(len(take)):
            if i in seen:
                continue
            ordered.append(take[i])
            if len(ordered) >= p.top_k:
                break

    return ordered[: p.top_k]
