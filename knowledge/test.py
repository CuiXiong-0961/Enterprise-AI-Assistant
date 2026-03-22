"""
knowledge 检索流水线示例：粗排（BM25 + 稠密）→ 融合（RRF）→ 精排（LLM）。

典型场景：在已用 ``repository/CppHeader`` 入库的 ``cpp_headers`` 集合里，
查「离散 / 采样」等相关声明。

---------------------------------------------------------------------------
使用前准备
---------------------------------------------------------------------------

1. 项目根目录安装依赖::

    pip install -r requirements.txt

2. 确保已把 ``RAG-corpus/Bugs`` 索引进 Chroma（与检索使用同一 embedding：BGE）::

    python -m repository.CppHeader.indexer

3. 精排会调用 ``utils/my_llm.py`` 里的 ``llm``（默认 DeepSeek），请配置好
   ``utils/env_utils`` 里对应 API Key；若只想看粗排+融合，加 ``--no-llm``。

---------------------------------------------------------------------------
怎么运行
---------------------------------------------------------------------------

在项目根目录 ``Enterprise-AI-Assistant`` 下::

    python knowledge/test.py

默认查询：头文件里与曲线/曲面离散、采样相关的函数。

自定义查询::

    python knowledge/test.py -q "有没有 submitAsync 异步提交"

只做粗排+融合（不调大模型，速度快）::

    python knowledge/test.py --no-llm

融合改加权、调整各路条数示例::

    python knowledge/test.py --fusion weighted --bm25-top 40 --dense-top 40 --fusion-top 25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from repository.chroma_crud import ChromaRepository  # noqa: E402
from repository.CppHeader import get_cpp_headers_collection  # noqa: E402

from knowledge import (  # noqa: E402
    CoarseRankingParams,
    FineRankingParams,
    FusionParams,
    fuse_ranked_lists,
    run_coarse_ranking,
    run_online_retrieval,
)


DEFAULT_QUERY = (
    "C++ 头文件里有哪些与曲线或曲面的离散、等参数采样、自适应离散、弧长离散相关的函数声明？"
)


def _print_fused(title: str, rows: list, *, show_text_chars: int = 500) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("(无结果)")
        return
    for i, r in enumerate(rows, 1):
        text = (getattr(r, "text", "") or "").replace("\r\n", "\n")
        if len(text) > show_text_chars:
            text = text[: show_text_chars - 3] + "..."
        print(f"\n[{i}] doc_id={r.doc_id}")
        print(f"    score={getattr(r, 'fused_score', '?')}  sources={getattr(r, 'sources', '')}")
        print(f"    text:\n{text}")


def demo_discretization_search(
    *,
    query: str,
    no_llm: bool,
    coarse: CoarseRankingParams,
    fusion: FusionParams,
    fine: FineRankingParams,
) -> None:
    repo = ChromaRepository()
    coll = get_cpp_headers_collection(repo)

    print("Chroma 路径:", repo.persist_path)
    print("查询:", query)

    if no_llm:
        coarse_res = run_coarse_ranking(
            query,
            params=coarse,
            chroma_collection=coll,
            candidate_pool=None,
        )
        print(
            f"\n粗排: BM25 {len(coarse_res.bm25_hits)} 条, "
            f"稠密 {len(coarse_res.dense_hits)} 条",
        )
        fused = fuse_ranked_lists(
            coarse_res.bm25_hits,
            coarse_res.dense_hits,
            params=fusion,
        )
        _print_fused(f"融合（{fusion.method}，top_m={fusion.fusion_top_m}）", fused)
        return

    final = run_online_retrieval(
        query,
        chroma_collection=coll,
        candidate_pool=None,
        coarse_params=coarse,
        fusion_params=fusion,
        fine_params=fine,
    )
    _print_fused(f"精排后 top_k={fine.top_k}", final)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="knowledge 检索示例（cpp_headers）")
    p.add_argument("-q", "--query", default=DEFAULT_QUERY, help="检索问句")
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="只做粗排+融合，不调用 utils.my_llm（无需大模型 Key）",
    )
    p.add_argument("--bm25-top", type=int, default=40, help="粗排 BM25 保留条数，默认 40")
    p.add_argument("--dense-top", type=int, default=40, help="粗排稠密检索条数，默认 40")
    p.add_argument("--fusion-top", type=int, default=25, help="融合后保留条数 fusion_top_m，默认 25")
    p.add_argument(
        "--fusion",
        choices=("rrf", "weighted"),
        default="rrf",
        help="融合策略：rrf 或 weighted，默认 rrf",
    )
    p.add_argument("--rrf-k", type=float, default=60.0, help="RRF 常数 k，默认 60")
    p.add_argument(
        "--w-bm25",
        type=float,
        default=0.5,
        help="加权融合时 BM25 权重，默认 0.5",
    )
    p.add_argument(
        "--w-dense",
        type=float,
        default=0.5,
        help="加权融合时稠密权重，默认 0.5",
    )
    p.add_argument("--fine-top", type=int, default=5, help="精排最终条数 top_k，默认 5")
    p.add_argument(
        "--fine-max-docs",
        type=int,
        default=12,
        help="送入 LLM 的最大文档数，默认 12",
    )
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    coarse = CoarseRankingParams(
        bm25_top_n=args.bm25_top,
        dense_top_n=args.dense_top,
    )
    fusion = FusionParams(
        method=args.fusion,
        fusion_top_m=args.fusion_top,
        rrf_k=args.rrf_k,
        weighted_alpha_bm25=args.w_bm25,
        weighted_alpha_dense=args.w_dense,
    )
    fine = FineRankingParams(
        top_k=args.fine_top,
        max_docs_for_llm=args.fine_max_docs,
    )
    demo_discretization_search(
        query=args.query,
        no_llm=args.no_llm,
        coarse=coarse,
        fusion=fusion,
        fine=fine,
    )


if __name__ == "__main__":
    main()
