"""Develop 文档索引器：将 RAG-corpus/Development 的 md 切分并写入 knowledge_docs。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer

from ..chroma_crud import ChromaRepository
from ..collections import CollectionName
from ..models import KnowledgeDocMetadata, metadata_to_chroma

from .constants import DEFAULT_DEVELOPMENT_CORPUS_DIR, EMBEDDING_MODEL_NAME
from .splitter import parse_doc_meta, split_markdown_parent_child

logger = logging.getLogger(__name__)


def get_knowledge_docs_collection(repo: ChromaRepository, *, model_name: str = EMBEDDING_MODEL_NAME) -> Any:
    """
    获取（或创建）使用本地 SentenceTransformer 模型的 `knowledge_docs` collection。

    注意：不要先调用 `ensure_collections()`，否则可能创建无 embedding 的集合。
    """
    ef = SentenceTransformerEmbeddingFunction(model_name=model_name, normalize_embeddings=True)
    return repo.client.get_or_create_collection(
        name=CollectionName.KNOWLEDGE_DOCS.value,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def index_development_corpus(
    corpus_dir: Path | None = None,
    *,
    chroma: ChromaRepository | None = None,
    clear_existing: bool = False,
    batch_size: int = 32,
    model_name: str = EMBEDDING_MODEL_NAME,
) -> int:
    """
    将 `RAG-corpus/Development` 下的 md 文档切分（父子索引），写入 `knowledge_docs`。

    - 父块：标题级摘要，parent_chunk_id = null
    - 子块：语义相似度切分，parent_chunk_id 指向父块
    """
    root = (corpus_dir or DEFAULT_DEVELOPMENT_CORPUS_DIR).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"语料目录不存在: {root}")

    repo = chroma or ChromaRepository()
    coll = get_knowledge_docs_collection(repo, model_name=model_name)

    if clear_existing:
        _clear_collection(coll)

    md_files = sorted(root.glob("*.md"))
    if not md_files:
        logger.warning("Development 目录下未找到 md: %s", root)
        return 0

    st_model = SentenceTransformer(model_name)

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

    for p in md_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        doc_meta = parse_doc_meta(p, corpus_root=root)

        parents, children = split_markdown_parent_child(text, model=st_model)

        doc_id = doc_meta.file_name

        # 写父块（先写，便于子块引用 parent_chunk_id）
        parent_id_map: dict[int, str] = {}
        for parent in parents:
            cid = _make_chunk_id(doc_id, "parent", parent.chunk_index, parent.text)
            parent_id_map[parent.chunk_index] = cid
            meta = KnowledgeDocMetadata(
                chunk_id=cid,
                doc_id=doc_id,
                file_name=doc_meta.file_name,
                parent_chunk_id=None,
                chunk_index=parent.chunk_index,
                topic=doc_meta.topic,
                title=doc_meta.topic,
                record_date=doc_meta.record_date,
                domain="development",
                section_title=parent.section_title,
                source_uri=p.as_posix(),
                data_source="RAG-corpus/Development",
            )
            extra = metadata_to_chroma(meta)
            extra["author"] = doc_meta.author
            ids_batch.append(cid)
            docs_batch.append(parent.text)
            meta_batch.append(extra)
            if len(ids_batch) >= batch_size:
                flush()

        # 写子块
        for child in children:
            cid = _make_chunk_id(doc_id, "child", child.chunk_index, child.text)
            meta = KnowledgeDocMetadata(
                chunk_id=cid,
                doc_id=doc_id,
                file_name=doc_meta.file_name,
                parent_chunk_id=child.parent_chunk_id,
                chunk_index=child.chunk_index,
                topic=doc_meta.topic,
                title=doc_meta.topic,
                record_date=doc_meta.record_date,
                domain="development",
                section_title=child.section_title,
                source_uri=p.as_posix(),
                data_source="RAG-corpus/Development",
            )
            extra = metadata_to_chroma(meta)
            extra["author"] = doc_meta.author
            extra["is_parent"] = False
            ids_batch.append(cid)
            docs_batch.append(child.text)
            meta_batch.append(extra)
            if len(ids_batch) >= batch_size:
                flush()

    flush()
    logger.info("已索引 %s 条 development 文档 chunk -> knowledge_docs（模型 %s）", total, model_name)
    return total


def _make_chunk_id(doc_id: str, kind: str, index: int, text: str) -> str:
    raw = f"{doc_id}|{kind}|{index}|{text[:320]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:28]
    return f"kd_{digest}"


def _clear_collection(coll: Any) -> None:
    batch = coll.get(include=[])
    ids = batch.get("ids") or []
    if ids:
        coll.delete(ids=ids)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    n = index_development_corpus(clear_existing=False)
    print(f"indexed_chunks={n}")


if __name__ == "__main__":
    main()

