"""
将 ``RAG-corpus/Bugs`` 头文件解析后写入 Chroma ``cpp_headers``；Embedding 通过
``sentence_transformers`` 加载 HuggingFace 上的 ``BAAI/bge-large-zh-v1.5``（Chroma 侧使用
``SentenceTransformerEmbeddingFunction``，无需 ``CHROMA_HUGGINGFACE_API_KEY``）。

metadata 一律经 ``CppHeaderMetadata`` + ``metadata_to_chroma``，与 ``repository/models.py`` 对齐。

注意：若本地 ``cpp_headers`` 曾用默认 MiniLM 建过库，向量维度与 BGE 不一致会导致报错，
需清空 ``repository/chroma_db`` 下数据或换用新目录后重新索引。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from ..chroma_crud import ChromaRepository
from ..collections import CollectionName
from ..models import CppHeaderMetadata, metadata_to_chroma

from .constants import DATA_SOURCE_RAG_CORPUS, DEFAULT_BUGS_CORPUS_DIR, EMBEDDING_MODEL_NAME
from .parser import iter_corpus_files, parse_header_file

logger = logging.getLogger(__name__)


def _make_chunk_id(rel_path: str, chunk: Any) -> str:
    raw = f"{rel_path}|{chunk.chunk_index}|{chunk.symbol_name}|{chunk.text[:320]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:28]
    return f"cpp_{digest}"


def _clear_collection(coll: Any) -> None:
    batch = coll.get(include=[])
    ids = batch.get("ids") or []
    if ids:
        coll.delete(ids=ids)


def get_cpp_headers_collection(
    repo: ChromaRepository,
    *,
    model_name: str = EMBEDDING_MODEL_NAME,
) -> Any:
    """获取（或创建）使用 BGE 中文向量的 ``cpp_headers`` collection。"""
    # 使用 SentenceTransformer 本地加载 HF 模型，无需 CHROMA_HUGGINGFACE_API_KEY
    ef = SentenceTransformerEmbeddingFunction(
        model_name=model_name,
        normalize_embeddings=True,
    )

    return repo.client.get_or_create_collection(
        name=CollectionName.CPP_HEADERS.value,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def index_bugs_corpus(
    corpus_dir: Path | None = None,
    *,
    chroma: ChromaRepository | None = None,
    clear_existing: bool = False,
    batch_size: int = 32,
    model_name: str = EMBEDDING_MODEL_NAME,
) -> int:
    """
    解析语料目录下头文件，批量写入 ``cpp_headers``。

    :return: 写入的片段条数。
    """
    root = (corpus_dir or DEFAULT_BUGS_CORPUS_DIR).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"语料目录不存在: {root}")

    repo = chroma or ChromaRepository()
    # 勿先调用 ``ensure_collections()``：否则会创建默认 embedding 的 cpp_headers，
    # 与 BGE 维度冲突。此处仅绑定 BGE 的 ``cpp_headers``。
    coll = get_cpp_headers_collection(repo, model_name=model_name)

    if clear_existing:
        _clear_collection(coll)

    files = iter_corpus_files(root)
    if not files:
        logger.warning("未找到任何头文件: %s", root)
        return 0

    ids_batch: list[str] = []
    docs_batch: list[str] = []
    meta_batch: list[dict[str, Any]] = []
    total = 0

    def flush() -> None:
        nonlocal total
        if not ids_batch:
            return
        coll.add(ids=ids_batch, documents=docs_batch, metadatas=meta_batch)
        total += len(ids_batch)
        ids_batch.clear()
        docs_batch.clear()
        meta_batch.clear()

    for path in files:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.name

        doc_id = rel
        for chunk in parse_header_file(path, rel_file_name=rel):
            cid = _make_chunk_id(rel, chunk)
            meta = CppHeaderMetadata(
                chunk_id=cid,
                doc_id=doc_id,
                file_name=rel,
                symbol_name=chunk.symbol_name,
                symbol_kind=chunk.symbol_kind,
                signature=chunk.signature,
                source_uri=path.as_posix(),
                data_source=DATA_SOURCE_RAG_CORPUS,
                chunk_index=chunk.chunk_index,
            )
            ids_batch.append(cid)
            docs_batch.append(chunk.text)
            meta_batch.append(metadata_to_chroma(meta))
            if len(ids_batch) >= batch_size:
                flush()

    flush()
    logger.info("已索引 %s 条 C++ 头文件片段 -> cpp_headers（模型 %s）", total, model_name)
    return total


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    n = index_bugs_corpus(clear_existing=True)
    print(f"indexed_chunks={n}")


if __name__ == "__main__":
    main()
