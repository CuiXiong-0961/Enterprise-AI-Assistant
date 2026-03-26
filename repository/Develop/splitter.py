"""Develop 文档切分：标题结构父块 + 语义相似度子块（<=300 tokens）。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from .constants import MAX_CHILD_TOKENS, SEMANTIC_SIM_THRESHOLD


@dataclass
class DocMeta:
    """从文件名/路径抽取的文档级元数据。"""

    author: str
    topic: str
    record_date: str
    file_name: str


@dataclass
class Chunk:
    """切分后的入库单元（父/子通用）。"""

    text: str
    section_title: str | None
    is_parent: bool
    chunk_index: int
    parent_chunk_id: str | None = None


_H_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_doc_meta(md_path: Path, *, corpus_root: Path) -> DocMeta:
    """
    命名约定：
    - 优先从文件名 `作者-主题-时间.md` 解析
    - 解析失败时回退为 unknown
    """
    rel = md_path.relative_to(corpus_root).as_posix()
    name = md_path.stem
    parts = name.split("-")
    author, topic, date = "unknown", name, "unknown"
    if len(parts) >= 3:
        author = parts[0].strip() or "unknown"
        topic = "-".join(parts[1:-1]).strip() or "unknown"
        date = parts[-1].strip() or "unknown"
    return DocMeta(author=author, topic=topic, record_date=date, file_name=rel)


def split_markdown_parent_child(
    md_text: str,
    *,
    model: SentenceTransformer,
    max_child_tokens: int = MAX_CHILD_TOKENS,
    sim_threshold: float = SEMANTIC_SIM_THRESHOLD,
) -> tuple[list[Chunk], list[Chunk]]:
    """
    返回 (parents, children)。

    parents：按标题层级形成的父块（章节/小节级）
    children：在每个父块内部按段落语义相似度聚合形成子块，并保证 <= max_child_tokens
    """
    sections = _split_by_headers(md_text)
    parents: list[Chunk] = []
    children: list[Chunk] = []

    parent_idx = 0
    child_idx = 0

    for sec_title, sec_body in sections:
        sec_title = sec_title.strip() if sec_title else ""
        parent_text = _build_parent_text(sec_title, sec_body)
        parent_chunk_id = _hash_id(f"parent|{parent_idx}|{sec_title}|{parent_text[:200]}")
        parents.append(
            Chunk(
                text=parent_text,
                section_title=sec_title or None,
                is_parent=True,
                chunk_index=parent_idx,
                parent_chunk_id=None,
            )
        )
        parent_idx += 1

        para_groups = _semantic_group_paragraphs(sec_body, model=model, sim_threshold=sim_threshold)
        for g in para_groups:
            for piece in _enforce_token_limit(g, max_tokens=max_child_tokens):
                child_text = _build_child_text(sec_title, piece)
                children.append(
                    Chunk(
                        text=child_text,
                        section_title=sec_title or None,
                        is_parent=False,
                        chunk_index=child_idx,
                        parent_chunk_id=parent_chunk_id,
                    )
                )
                child_idx += 1

    # 无标题文档兜底：整篇作为一个父块 + 若干子块
    if not parents and md_text.strip():
        parent_text = _build_parent_text("", md_text)
        parent_chunk_id = _hash_id(f"parent|0|{parent_text[:200]}")
        parents = [Chunk(text=parent_text, section_title=None, is_parent=True, chunk_index=0)]
        para_groups = _semantic_group_paragraphs(md_text, model=model, sim_threshold=sim_threshold)
        for g in para_groups:
            for piece in _enforce_token_limit(g, max_tokens=max_child_tokens):
                children.append(
                    Chunk(
                        text=piece.strip(),
                        section_title=None,
                        is_parent=False,
                        chunk_index=len(children),
                        parent_chunk_id=parent_chunk_id,
                    )
                )

    return parents, children


def _split_by_headers(md_text: str) -> list[tuple[str, str]]:
    """
    粗切：按 markdown 标题分块。
    返回 list[(section_title, section_body)]。section_title 不含 # 号。
    """
    lines = md_text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    cur_title = ""
    cur_body: list[str] = []
    for ln in lines:
        m = _H_RE.match(ln)
        if m:
            # flush old
            if cur_body or cur_title:
                blocks.append((cur_title, cur_body))
            cur_title = (m.group(2) or "").strip()
            cur_body = []
        else:
            cur_body.append(ln)
    if cur_body or cur_title:
        blocks.append((cur_title, cur_body))
    # 移除空块
    out: list[tuple[str, str]] = []
    for t, b in blocks:
        body = "\n".join(b).strip()
        if (t or "").strip() or body:
            out.append((t, body))
    return out


def _semantic_group_paragraphs(text: str, *, model: SentenceTransformer, sim_threshold: float) -> list[str]:
    """
    语义分组：先按空行切段落，对相邻段落做相似度判断，低于阈值则断开。
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paras:
        return []
    if len(paras) == 1:
        return [paras[0]]

    embs = model.encode(paras, normalize_embeddings=True)
    groups: list[list[str]] = [[paras[0]]]
    for i in range(1, len(paras)):
        a = embs[i - 1]
        b = embs[i]
        sim = float(np.dot(a, b))
        if sim >= sim_threshold:
            groups[-1].append(paras[i])
        else:
            groups.append([paras[i]])
    return ["\n\n".join(g).strip() for g in groups if any(x.strip() for x in g)]


def _estimate_tokens(text: str) -> int:
    # 简化 token 估算：中英混排大致 2 字符 ~ 1 token
    s = (text or "").strip()
    if not s:
        return 0
    return max(1, len(s) // 2)


def _enforce_token_limit(text: str, *, max_tokens: int) -> list[str]:
    """
    若 text 超过 token 上限，按句子/换行边界继续拆分。
    """
    s = text.strip()
    if not s:
        return []
    if _estimate_tokens(s) <= max_tokens:
        return [s]

    # 先按句号/分号/换行粗切
    parts = [p.strip() for p in re.split(r"(?<=[。！？；;])\s+|\n+", s) if p.strip()]
    if not parts:
        return [s[: max(50, max_tokens * 2)]]

    out: list[str] = []
    buf: list[str] = []
    for p in parts:
        candidate = ("\n".join(buf + [p])).strip()
        if buf and _estimate_tokens(candidate) > max_tokens:
            out.append("\n".join(buf).strip())
            buf = [p]
        else:
            buf.append(p)
    if buf:
        out.append("\n".join(buf).strip())

    # 最后兜底：仍超限则硬截断（尽量少发生）
    final: list[str] = []
    for x in out:
        if _estimate_tokens(x) <= max_tokens:
            final.append(x)
        else:
            final.append(x[: max_tokens * 2].rstrip() + "…")
    return final


def _build_parent_text(section_title: str, body: str) -> str:
    title = section_title.strip()
    snippet = body.strip().replace("\r\n", "\n")
    if len(snippet) > 600:
        snippet = snippet[:597] + "..."
    if title:
        return f"{title}\n\n{snippet}".strip()
    return snippet.strip()


def _build_child_text(section_title: str, body: str) -> str:
    title = section_title.strip()
    b = body.strip()
    if title and not b.startswith(title):
        return f"{title}\n\n{b}".strip()
    return b


def _hash_id(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:28]

