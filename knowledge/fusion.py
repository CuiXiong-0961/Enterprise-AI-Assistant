"""
线上检索 — 融合层：RRF（倒数排名融合）与加权分数融合。

输入为粗排两路 ``RankedDocument`` 列表；输出统一为 ``FusedDocument``，供精排使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .coarse_ranking import RankedDocument


@dataclass
class FusedDocument:
    doc_id: str
    text: str
    fused_score: float
    fusion_rank: int
    sources: str = ""
    """如 ``bm25+dense``，便于调试。"""


@dataclass
class FusionParams:
    """融合策略与超参数。"""

    method: Literal["rrf", "weighted"] = "rrf"
    """``rrf``：倒数排名融合；``weighted``：对两路分数做加权。"""
    fusion_top_m: int = 30
    """融合后保留的最大条数（进入精排前的宽度）。"""
    rrf_k: float = 60.0
    """RRF 平滑常数，常见取值 60；越小则高排名项权重越大。"""
    weighted_alpha_bm25: float = 0.5
    """加权融合时 BM25 分支权重（归一化分数）。"""
    weighted_alpha_dense: float = 0.5
    """加权融合时稠密分支权重（归一化分数）。"""

    def __post_init__(self) -> None:
        if self.rrf_k <= 0:
            raise ValueError("rrf_k 须为正数")
        if self.fusion_top_m <= 0:
            raise ValueError("fusion_top_m 须为正整数")
        if self.method == "weighted":
            s = self.weighted_alpha_bm25 + self.weighted_alpha_dense
            if s <= 0:
                raise ValueError("加权系数之和须大于 0")


def reciprocal_rank_fusion(
    bm25_hits: list[RankedDocument],
    dense_hits: list[RankedDocument],
    *,
    k: float,
    top_m: int,
) -> list[FusedDocument]:
    """RRF：score(d) = Σ 1/(k + rank)（每路列表内 rank 从 1 开始）。"""
    scores: dict[str, float] = {}
    texts: dict[str, str] = {}
    src: dict[str, set[str]] = {}

    def add_list(hits: list[RankedDocument], name: str) -> None:
        for r, h in enumerate(hits, start=1):
            scores[h.doc_id] = scores.get(h.doc_id, 0.0) + 1.0 / (k + r)
            texts.setdefault(h.doc_id, h.text)
            src.setdefault(h.doc_id, set()).add(name)

    add_list(bm25_hits, "bm25")
    add_list(dense_hits, "dense")

    order = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)[:top_m]
    out: list[FusedDocument] = []
    for i, doc_id in enumerate(order):
        out.append(
            FusedDocument(
                doc_id=doc_id,
                text=texts.get(doc_id, ""),
                fused_score=scores[doc_id],
                fusion_rank=i,
                sources="+".join(sorted(src.get(doc_id, set()))),
            )
        )
    return out


def _min_max_norm(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    xs = list(values.values())
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-12:
        return {k: 1.0 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def weighted_fusion(
    bm25_hits: list[RankedDocument],
    dense_hits: list[RankedDocument],
    *,
    alpha_bm25: float,
    alpha_dense: float,
    top_m: int,
) -> list[FusedDocument]:
    """对两路 ``score`` 分别 min-max 归一化后线性加权。"""
    b_scores = {h.doc_id: h.score for h in bm25_hits}
    d_scores = {h.doc_id: h.score for h in dense_hits}
    texts: dict[str, str] = {}
    for h in bm25_hits + dense_hits:
        texts.setdefault(h.doc_id, h.text)

    nb = _min_max_norm(b_scores)
    nd = _min_max_norm(d_scores)
    all_ids = set(nb) | set(nd)
    combined: dict[str, float] = {}
    src: dict[str, set[str]] = {}
    for doc_id in all_ids:
        sb = nb.get(doc_id, 0.0)
        sd = nd.get(doc_id, 0.0)
        combined[doc_id] = alpha_bm25 * sb + alpha_dense * sd
        if doc_id in nb:
            src.setdefault(doc_id, set()).add("bm25")
        if doc_id in nd:
            src.setdefault(doc_id, set()).add("dense")

    order = sorted(combined.keys(), key=lambda d: combined[d], reverse=True)[:top_m]
    out: list[FusedDocument] = []
    for i, doc_id in enumerate(order):
        out.append(
            FusedDocument(
                doc_id=doc_id,
                text=texts.get(doc_id, ""),
                fused_score=combined[doc_id],
                fusion_rank=i,
                sources="+".join(sorted(src.get(doc_id, set()))),
            )
        )
    return out


def fuse_ranked_lists(
    bm25_hits: list[RankedDocument],
    dense_hits: list[RankedDocument],
    *,
    params: FusionParams | None = None,
) -> list[FusedDocument]:
    p = params or FusionParams()
    if p.method == "rrf":
        return reciprocal_rank_fusion(
            bm25_hits,
            dense_hits,
            k=p.rrf_k,
            top_m=p.fusion_top_m,
        )
    return weighted_fusion(
        bm25_hits,
        dense_hits,
        alpha_bm25=p.weighted_alpha_bm25,
        alpha_dense=p.weighted_alpha_dense,
        top_m=p.fusion_top_m,
    )
