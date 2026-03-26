"""Memory 存储基础设施：封装 JSON 读写和目录初始化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import DATA_ROOT, SHORT_TERM_DIR, USER_PROFILE_DIR, VECTOR_DB_DIR, WINDOW_META_DIR


def ensure_memory_dirs() -> None:
    for p in (DATA_ROOT, SHORT_TERM_DIR, USER_PROFILE_DIR, WINDOW_META_DIR, VECTOR_DB_DIR):
        p.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

