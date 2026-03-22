"""
线上检索 — 粗排层：BM25（词法） + 稠密检索（Chroma 向量库）。

调用方传入候选池与/或已绑定向量模型的 Chroma collection；参数均由 ``CoarseRankingParams`` 暴露。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from rank_bm25 import BM25Okapi

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class DocumentCandidate:
    """一条可供 BM25 与融合使用的文档。"""

    doc_id: str
    text: str


@dataclass
class RankedDocument:
    """粗排输出的一条结果。"""

    doc_id: str
    text: str
    score: float
    rank: int
    source: Literal["bm25", "dense"]


@dataclass
class CoarseRankingParams:
    """粗排超参数（均可由调用方覆盖）。"""

    bm25_top_n: int = 50
    """BM25 保留的条数上限。"""
    dense_top_n: int = 50
    """稠密检索（Chroma query）返回条数上限。"""
    bm25_tokenizer: Callable[[str], list[str]] | None = None
    """分词函数；默认中英混排启发式切分。"""


@dataclass
class CoarseRankingResult:
    bm25_hits: list[RankedDocument] = field(default_factory=list)
    dense_hits: list[RankedDocument] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 分词与 BM25
# ---------------------------------------------------------------------------


def default_bm25_tokenize(text: str) -> list[str]:
    """英文/数字/下划线 + 连续汉字，适合代码与中文注释混合。"""
    if not text:
        return []
    parts = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|\d+|[\u4e00-\u9fff]+", text.lower())
    return [p for p in parts if p]


def bm25_coarse_rank(
    query: str,
    candidates: list[DocumentCandidate],
    *,
    top_n: int,
    tokenize: Callable[[str], list[str]] | None = None,
) -> list[RankedDocument]:
    if not candidates or top_n <= 0:
        return []
    tok = tokenize or default_bm25_tokenize
    corpus_tokens = [tok(c.text) for c in candidates]
    if all(not t for t in corpus_tokens):
        return []
    bm25 = BM25Okapi(corpus_tokens)
    q_tok = tok(query)
    if not q_tok:
        scores = [0.0] * len(candidates)
    else:
        scores = bm25.get_scores(q_tok)
    order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)[:top_n]
    out: list[RankedDocument] = []
    for r, i in enumerate(order):
        out.append(
            RankedDocument(
                doc_id=candidates[i].doc_id,
                text=candidates[i].text,
                score=float(scores[i]),
                rank=r,
                source="bm25",
            )
        )
    return out


def _distance_to_similarity(distance: float | None) -> float:
    if distance is None:
        return 0.0
    d = float(distance)
    return 1.0 / (1.0 + max(d, 0.0))


def dense_coarse_rank_chroma(
    collection: Any,
    query: str,
    *,
    top_n: int,
    include: list[str] | None = None,
) -> list[RankedDocument]:
    """
    使用 Chroma collection 的默认 embedding 做 query（稠密检索）。

    ``collection`` 须为 ``chromadb`` 的 Collection，且已配置 embedding_function。
    """
    if top_n <= 0:
        return []
    inc = include or ["documents", "metadatas", "distances"]
    raw = collection.query(query_texts=[query], n_results=top_n, include=inc)
    ids = (raw.get("ids") or [[]])[0] or []
    docs = (raw.get("documents") or [[]])[0] or []
    dists = (raw.get("distances") or [[]])[0] if "distances" in inc else None
    out: list[RankedDocument] = []
    for r, doc_id in enumerate(ids):
        text = docs[r] if r < len(docs) else ""
        d = dists[r] if dists is not None and r < len(dists) else None
        score = _distance_to_similarity(d)
        out.append(
            RankedDocument(
                doc_id=str(doc_id),
                text=text or "",
                score=score,
                rank=r,
                source="dense",
            ),
        )
    return out


def _merge_candidate_pool(
    explicit: list[DocumentCandidate] | None,
    dense_hits: list[RankedDocument],
) -> list[DocumentCandidate]:
    by_id: dict[str, DocumentCandidate] = {}
    for c in explicit or []:
        by_id[c.doc_id] = c
    for h in dense_hits:
        if h.doc_id not in by_id:
            by_id[h.doc_id] = DocumentCandidate(doc_id=h.doc_id, text=h.text)
    return list(by_id.values())


def run_coarse_ranking(
    query: str,
    *,
    params: CoarseRankingParams | None = None,
    candidate_pool: list[DocumentCandidate] | None = None,
    chroma_collection: Any | None = None,
) -> CoarseRankingResult:
    """
    同时跑稠密（可选）与 BM25。

    - 若提供 ``chroma_collection``：先 ``dense_top_n`` 稠密检索。
    - BM25 在 ``candidate_pool`` 与稠密结果的并集上截断至 ``bm25_top_n``（若并集为空则 BM25 为空）。
    """
    p = params or CoarseRankingParams()
    tokenize = p.bm25_tokenizer or default_bm25_tokenize

    dense_hits: list[RankedDocument] = []
    if chroma_collection is not None:
        dense_hits = dense_coarse_rank_chroma(
            chroma_collection,
            query,
            top_n=p.dense_top_n,
        )

    pool = _merge_candidate_pool(candidate_pool, dense_hits)
    bm25_hits = bm25_coarse_rank(
        query,
        pool,
        top_n=p.bm25_top_n,
        tokenize=tokenize,
    )

    return CoarseRankingResult(bm25_hits=bm25_hits, dense_hits=dense_hits)
