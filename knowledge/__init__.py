"""
知识库与线上检索编排：粗排（BM25 + 稠密）→ 融合（RRF / 加权）→ 精排（LLM）。
"""

from __future__ import annotations

from typing import Any

from .coarse_ranking import (
    CoarseRankingParams,
    CoarseRankingResult,
    DocumentCandidate,
    RankedDocument,
    bm25_coarse_rank,
    dense_coarse_rank_chroma,
    run_coarse_ranking,
)
from .fine_ranking import FineRankingParams, fine_rerank_llm
from .fusion import FusedDocument, FusionParams, fuse_ranked_lists, reciprocal_rank_fusion, weighted_fusion


def run_online_retrieval(
    query: str,
    *,
    chroma_collection: Any | None = None,
    candidate_pool: list[DocumentCandidate] | None = None,
    coarse_params: CoarseRankingParams | None = None,
    fusion_params: FusionParams | None = None,
    fine_params: FineRankingParams | None = None,
    llm: Any | None = None,
) -> list[FusedDocument]:
    """
    串联粗排 → 融合 → 精排，返回精排后的 ``FusedDocument`` 列表。

    - ``chroma_collection``：可选；提供则做稠密检索（须已配置 embedding_function）。
    - ``candidate_pool``：可选；与稠密结果并集后供 BM25 使用。
    """
    coarse = run_coarse_ranking(
        query,
        params=coarse_params,
        candidate_pool=candidate_pool,
        chroma_collection=chroma_collection,
    )
    fused = fuse_ranked_lists(
        coarse.bm25_hits,
        coarse.dense_hits,
        params=fusion_params,
    )
    return fine_rerank_llm(query, fused, params=fine_params, llm=llm)


__all__ = [
    "CoarseRankingParams",
    "CoarseRankingResult",
    "DocumentCandidate",
    "RankedDocument",
    "bm25_coarse_rank",
    "dense_coarse_rank_chroma",
    "run_coarse_ranking",
    "FusionParams",
    "FusedDocument",
    "fuse_ranked_lists",
    "reciprocal_rank_fusion",
    "weighted_fusion",
    "FineRankingParams",
    "fine_rerank_llm",
    "run_online_retrieval",
]
