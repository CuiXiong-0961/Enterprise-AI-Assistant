"""Memory 模块常量定义：集中维护默认阈值与路径。"""

from __future__ import annotations

from pathlib import Path

MEMORY_ROOT = Path(__file__).resolve().parent
DATA_ROOT = MEMORY_ROOT / "data"

SHORT_TERM_MAX_TURNS = 5
PROFILE_TOKEN_LIMIT = 800

WINDOW_TURNS = 50
WINDOW_KEEP_MAX = 5

USER_PROFILE_DIR = DATA_ROOT / "profiles"
SHORT_TERM_DIR = DATA_ROOT / "short_term"
WINDOW_META_DIR = DATA_ROOT / "windows"
VECTOR_DB_DIR = DATA_ROOT / "vector_db"

