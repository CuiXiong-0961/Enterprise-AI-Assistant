"""Develop 文档入库常量：语料路径、模型、切分阈值。"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent

DEFAULT_DEVELOPMENT_CORPUS_DIR = PROJECT_ROOT / "RAG-corpus" / "Development"

# 与 CppHeader 保持一致：本地 sentence-transformers 加载 HF 模型
EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"

# 子 chunk 最大 token（硬上限）
MAX_CHILD_TOKENS = 300

# 语义相似度阈值：相邻段落低于该值则断开
SEMANTIC_SIM_THRESHOLD = 0.78

