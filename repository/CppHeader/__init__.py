"""C++ 头文件语料解析与 BGE 向量入库（``cpp_headers``）。

``indexer`` 依赖 chromadb / sentence_transformers，采用惰性导入，避免仅使用 ``parser`` 时拉起重依赖。
"""

from __future__ import annotations

from typing import Any

from .constants import (
    DATA_SOURCE_RAG_CORPUS,
    DEFAULT_BUGS_CORPUS_DIR,
    EMBEDDING_MODEL_NAME,
    HEADER_SUFFIXES,
    MAX_EMBED_CHARS,
    PROJECT_ROOT,
)
from .parser import HeaderChunk, iter_corpus_files, parse_header_file


def get_cpp_headers_collection(repo: Any, **kwargs: Any) -> Any:
    from .indexer import get_cpp_headers_collection as _fn

    return _fn(repo, **kwargs)


def index_bugs_corpus(corpus_dir: Any = None, **kwargs: Any) -> int:
    from .indexer import index_bugs_corpus as _fn

    return _fn(corpus_dir, **kwargs)


__all__ = [
    "DATA_SOURCE_RAG_CORPUS",
    "DEFAULT_BUGS_CORPUS_DIR",
    "EMBEDDING_MODEL_NAME",
    "HEADER_SUFFIXES",
    "MAX_EMBED_CHARS",
    "PROJECT_ROOT",
    "HeaderChunk",
    "get_cpp_headers_collection",
    "index_bugs_corpus",
    "iter_corpus_files",
    "parse_header_file",
]
