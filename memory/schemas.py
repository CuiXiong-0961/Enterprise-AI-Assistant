"""Memory 数据结构定义：统一短时、画像、窗口摘要的字段。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TurnRecord:
    """一轮对话（用户输入 + 助手回复）。"""

    turn_id: int
    timestamp: str
    user_message: str
    assistant_message: str
    intent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UserProfile:
    """用户画像（长时记忆-结构化 JSON）。"""

    basic_profile: dict[str, Any] = field(default_factory=dict)
    interaction_habits: dict[str, Any] = field(default_factory=dict)
    special_requirements: dict[str, Any] = field(default_factory=dict)
    topic_memory: list[str] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    last_updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryWindow:
    """50 轮压缩摘要窗口（长时记忆-向量检索）。"""

    window_id: str
    user_id: str
    start_turn_id: int
    end_turn_id: int
    created_at: str
    time_range: str
    summary: str
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

