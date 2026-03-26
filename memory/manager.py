"""Memory 统一入口：编排短时记忆、用户画像与窗口压缩检索。"""

from __future__ import annotations

from typing import Any

from .profile_store import UserProfileStore
from .schemas import TurnRecord
from .short_term import ShortTermMemoryStore
from .window_store import ConversationWindowStore


class MemoryManager:
    """对外提供单一调用接口，便于挂载到 LangGraph 节点。"""

    def __init__(self) -> None:
        self.short_term = ShortTermMemoryStore()
        self.profile = UserProfileStore()
        self.windows = ConversationWindowStore()

    def record_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
        *,
        intent: str | None = None,
        profile_updates: dict[str, Any] | None = None,
        update_profile: bool = True,
    ) -> dict[str, Any]:
        rec = self.short_term.append_turn(
            user_id=user_id,
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
        )

        if update_profile:
            profile = self.profile.update(
                user_id,
                occupation=(profile_updates or {}).get("occupation"),
                habits=(profile_updates or {}).get("habits"),
                hard_constraints=(profile_updates or {}).get("hard_constraints"),
                soft_preferences=(profile_updates or {}).get("soft_preferences"),
                topics=(profile_updates or {}).get("topics"),
            )
        else:
            profile = self.profile.load(user_id)

        new_window = self.windows.append_turn_and_maybe_compress(user_id, rec)
        return {
            "turn": rec.to_dict(),
            "profile": profile.to_dict(),
            "new_window": new_window.to_dict() if new_window else None,
        }

    def build_context(self, user_id: str, query: str, *, top_k_windows: int = 2) -> dict[str, Any]:
        recent_turns = [t.to_dict() for t in self.short_term.get_recent_turns(user_id)]
        profile = self.profile.load(user_id).to_dict()
        recalled_windows = self.windows.retrieve(user_id, query=query, top_k=top_k_windows)
        return {
            "recent_turns": recent_turns,
            "profile": profile,
            "recalled_windows": recalled_windows,
        }

    def record_existing_turn(self, user_id: str, turn: TurnRecord) -> dict[str, Any]:
        """兼容已有流水线中已经生成 TurnRecord 的场景。"""
        rec = self.short_term.append_turn(
            user_id=user_id,
            user_message=turn.user_message,
            assistant_message=turn.assistant_message,
            intent=turn.intent,
            turn_id=turn.turn_id,
        )
        new_window = self.windows.append_turn_and_maybe_compress(user_id, rec)
        return {"turn": rec.to_dict(), "new_window": new_window.to_dict() if new_window else None}

