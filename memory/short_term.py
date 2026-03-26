"""短时记忆模块：维护每个用户最近 5 轮对话上下文。"""

from __future__ import annotations

from pathlib import Path

from .constants import SHORT_TERM_DIR, SHORT_TERM_MAX_TURNS
from .schemas import TurnRecord, utc_now_iso
from .storage import ensure_memory_dirs, read_json, write_json


class ShortTermMemoryStore:
    """为上下文工程提供最近 N 轮对话（默认 5 轮）。"""

    def __init__(self, max_turns: int = SHORT_TERM_MAX_TURNS) -> None:
        ensure_memory_dirs()
        self.max_turns = max_turns

    def _path(self, user_id: str) -> Path:
        return SHORT_TERM_DIR / f"{user_id}.json"

    def get_recent_turns(self, user_id: str) -> list[TurnRecord]:
        raw = read_json(self._path(user_id), default=[])
        out: list[TurnRecord] = []
        for item in raw:
            out.append(
                TurnRecord(
                    turn_id=int(item.get("turn_id", 0)),
                    timestamp=str(item.get("timestamp", utc_now_iso())),
                    user_message=str(item.get("user_message", "")),
                    assistant_message=str(item.get("assistant_message", "")),
                    intent=item.get("intent"),
                )
            )
        return out[-self.max_turns :]

    def append_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
        *,
        intent: str | None = None,
        turn_id: int | None = None,
    ) -> TurnRecord:
        turns = self.get_recent_turns(user_id)
        next_turn_id = turn_id if turn_id is not None else (turns[-1].turn_id + 1 if turns else 1)
        rec = TurnRecord(
            turn_id=next_turn_id,
            timestamp=utc_now_iso(),
            user_message=user_message.strip(),
            assistant_message=assistant_message.strip(),
            intent=intent,
        )
        turns.append(rec)
        turns = turns[-self.max_turns :]
        write_json(self._path(user_id), [t.to_dict() for t in turns])
        return rec

