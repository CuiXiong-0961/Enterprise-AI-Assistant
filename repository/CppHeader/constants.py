"""C++ 头文件入库：语料路径与 Embedding 模型。"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
# repository/CppHeader -> repository -> 项目根
PROJECT_ROOT = PACKAGE_DIR.parent.parent

DEFAULT_BUGS_CORPUS_DIR = PROJECT_ROOT / "RAG-corpus" / "Bugs"

HEADER_SUFFIXES = (".hxx", ".hpp", ".hh", ".h")

# HuggingFace：中文检索常用 BGE（与 Chroma HuggingFaceEmbeddingFunction 配合）
EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"

# BGE 系列建议短文本；过长则截断避免异常（token 约 512）
MAX_EMBED_CHARS = 1800

DATA_SOURCE_RAG_CORPUS = "RAG-corpus/Bugs"
