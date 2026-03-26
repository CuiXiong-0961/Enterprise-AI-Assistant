"""知识文档检索输出：从 knowledge_docs 召回 chunk，并格式化为可读答案（含来源）。"""

from __future__ import annotations

from typing import Any


def retrieve_knowledge_docs(collection: Any, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    raw = collection.query(
        query_texts=[query],
        n_results=max(1, top_k),
        include=["documents", "metadatas", "distances"],
    )
    ids = (raw.get("ids") or [[]])[0] or []
    docs = (raw.get("documents") or [[]])[0] or []
    metas = (raw.get("metadatas") or [[]])[0] or []
    dists = (raw.get("distances") or [[]])[0] or []

    out: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        out.append(
            {
                "id": str(doc_id),
                "text": (docs[i] if i < len(docs) else "") or "",
                "meta": meta if isinstance(meta, dict) else {},
                "distance": float(dists[i]) if i < len(dists) and dists[i] is not None else None,
            }
        )
    return out


def format_knowledge_answer(query: str, hits: list[dict[str, Any]], *, show_chars: int = 320) -> str:
    if not hits:
        return "**我不知道 / 当前无法确认**（在知识库中未检索到相关内容）。"

    lines: list[str] = []
    lines.append(f"### 检索结果（knowledge_docs）")
    lines.append(f"- **问题**：{query}")
    lines.append("")

    for idx, h in enumerate(hits, 1):
        meta = h.get("meta") or {}
        file_name = meta.get("file_name") or meta.get("source_uri") or "unknown"
        author = meta.get("author") or "unknown"
        record_date = meta.get("record_date") or "unknown"
        section_title = meta.get("section_title") or meta.get("title") or meta.get("topic") or ""
        text = (h.get("text") or "").replace("\r\n", "\n").strip()
        if len(text) > show_chars:
            text = text[: show_chars - 3] + "..."
        lines.append(f"#### [{idx}] {section_title}".strip())
        lines.append(f"- **作者**：{author}  **时间**：{record_date}")
        lines.append(f"- **来源**：{file_name}")
        lines.append("")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


__all__ = ["retrieve_knowledge_docs", "format_knowledge_answer"]

