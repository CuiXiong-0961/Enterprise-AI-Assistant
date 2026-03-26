"""C++ 头文件检索路径：Chroma 召回 + LLM 生成答案与置信度（JSON）。"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


@dataclass
class CppAnswerResult:
    """Cpp 路径单次调用的结构化结果。"""

    assistant_text: str
    confidence: float
    sources: list[str]
    update_profile: bool
    raw_llm: str | None = None


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```\w*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _parse_llm_json_obj(raw: str) -> dict[str, Any]:
    s = _strip_code_fence(raw)
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return {}
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def retrieve_cpp_chunks(
    collection: Any,
    query: str,
    *,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    """从 cpp_headers 集合拉取文档与 metadata，供拼装上下文。"""
    raw = collection.query(
        query_texts=[query],
        n_results=max(1, top_k),
        include=["documents", "metadatas", "distances"],
    )
    ids = (raw.get("ids") or [[]])[0] or []
    docs = (raw.get("documents") or [[]])[0] or []
    metas = (raw.get("metadatas") or [[]])[0] or []
    out: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else None
        text = docs[i] if i < len(docs) else ""
        if isinstance(meta, dict):
            file_name = meta.get("file_name") or ""
            source_uri = meta.get("source_uri") or ""
        else:
            file_name, source_uri = "", ""
        out.append(
            {
                "id": str(doc_id),
                "text": text or "",
                "file_name": str(file_name),
                "source_uri": str(source_uri),
            }
        )
    return out


def _format_context_block(chunks: list[dict[str, Any]], max_chars: int = 8000) -> str:
    parts: list[str] = []
    used = 0
    for i, c in enumerate(chunks, 1):
        src = c.get("file_name") or c.get("source_uri") or c.get("id", "")
        block = f"[{i}] 来源: {src}\n{c.get('text', '')}\n"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)


def run_cpp_answer(
    user_message: str,
    collection: Any,
    *,
    llm: Any | None = None,
    top_k: int = 6,
) -> CppAnswerResult:
    """
    检索 + LLM。要求模型仅输出 JSON：
    answer, confidence(0-100), sources(字符串列表), can_confirm(bool)。
    """
    chunks = retrieve_cpp_chunks(collection, user_message, top_k=top_k)
    has_usable_source = any(
        (c.get("file_name") or c.get("source_uri")) and (c.get("text") or "").strip()
        for c in chunks
    )

    if not chunks or not has_usable_source:
        hint = (
            "可根据问题中的类名/函数名到代码仓库中搜索对应头文件；"
            "或先运行 `python -m repository.CppHeader.indexer` 建立向量库后再试。"
        )
        return CppAnswerResult(
            assistant_text=f"**我不知道 / 当前无法确认**（检索未命中有效片段或缺少可引用来源）。\n\n{hint}",
            confidence=0.0,
            sources=[],
            update_profile=False,
        )

    context = _format_context_block(chunks)
    source_list = sorted(
        {c.get("file_name") or c.get("source_uri") for c in chunks if c.get("file_name") or c.get("source_uri")}
    )

    try:
        from utils.my_llm import llm as default_llm
    except Exception as e:
        logger.warning("无法加载 LLM：%s", e)
        lines = "\n".join(f"- {s}" for s in source_list[:8])
        return CppAnswerResult(
            assistant_text=(
                "**当前无法完成生成**（大模型未配置或加载失败）。\n\n"
                f"检索到的参考来源（节选）：\n{lines}"
            ),
            confidence=0.0,
            sources=source_list,
            update_profile=False,
        )

    model = llm or default_llm
    sys_prompt = (
        "你是企业 C++ 技术助手。下面「检索片段」来自头文件向量库，可能不完整。\n"
        "规则：\n"
        "1. 只能依据检索片段作答；不得编造 API、数值或文件路径。\n"
        "2. 若无法从片段中确认事实或数值，须在 answer 中明确写「我不知道」或「当前无法确认」。\n"
        "3. 能确认时必须在 answer 末尾用单独一行列出来源，格式：来源：<文件或路径>（可多个）。\n"
        "4. 仅输出一个 JSON 对象，不要 markdown，键为："
        'answer(字符串), confidence(0-100数字), sources(字符串数组，与引用一致), can_confirm(布尔)。\n'
        "5. 若无法确认，can_confirm 为 false，confidence 应偏低（如 0-40）。\n"
    )
    user_block = f"用户问题：{user_message.strip()}\n\n检索片段：\n{context}"
    try:
        resp = model.invoke(
            [
                HumanMessage(content=sys_prompt + "\n\n" + user_block),
            ]
        )
        raw = getattr(resp, "content", None) or ""
    except Exception as e:
        logger.exception("LLM 生成失败：%s", e)
        lines = "\n".join(f"- {s}" for s in source_list[:8])
        return CppAnswerResult(
            assistant_text=(
                "**当前无法完成生成**（模型调用异常）。\n\n"
                f"检索到的参考来源：\n{lines}"
            ),
            confidence=0.0,
            sources=source_list,
            update_profile=False,
            raw_llm=None,
        )

    data = _parse_llm_json_obj(raw)
    answer = str(data.get("answer", "")).strip()
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    src_from_model = data.get("sources")
    if isinstance(src_from_model, list):
        sources_out = [str(x) for x in src_from_model if str(x).strip()]
    else:
        sources_out = list(source_list)

    can_confirm = bool(data.get("can_confirm", False))

    if not answer:
        answer = "当前无法从检索结果中生成有效回答。"

    update_profile = confidence > 80 and bool(sources_out) and can_confirm

    footer = ""
    if sources_out:
        footer = "\n\n**引用来源**：\n" + "\n".join(f"- {s}" for s in sources_out[:12])
    assistant_text = answer + footer

    return CppAnswerResult(
        assistant_text=assistant_text,
        confidence=confidence,
        sources=sources_out,
        update_profile=update_profile,
        raw_llm=raw,
    )
