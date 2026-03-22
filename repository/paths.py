"""Repository 内路径约定：Chroma 持久化目录等。"""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT: Path = Path(__file__).resolve().parent

# 与 schema.md「与后续实现的衔接」一致：向量库文件放在本包下单独目录，不入库提交
DEFAULT_CHROMA_PERSIST_DIR: Path = REPOSITORY_ROOT / "chroma_db"
