"""长时记忆-用户画像模块：维护 <=800 tokens 的结构化 JSON。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import PROFILE_TOKEN_LIMIT, USER_PROFILE_DIR
from .schemas import UserProfile, utc_now_iso
from .storage import ensure_memory_dirs, read_json, write_json


def _estimate_tokens(text: str) -> int:
    # 简化估算：中英文混合场景下使用字符长度近似，避免引入额外 tokenizer 依赖。
    return max(1, len(text) // 2)


class UserProfileStore:
    """管理用户画像读写、增量更新与预算压缩。"""

    def __init__(self, token_limit: int = PROFILE_TOKEN_LIMIT) -> None:
        ensure_memory_dirs()
        self.token_limit = token_limit

    def _path(self, user_id: str) -> Path:
        return USER_PROFILE_DIR / f"{user_id}.json"

    def load(self, user_id: str) -> UserProfile:
        raw = read_json(self._path(user_id), default={})
        return UserProfile(
            basic_profile=raw.get("basic_profile", {}),
            interaction_habits=raw.get("interaction_habits", {}),
            special_requirements=raw.get("special_requirements", {}),
            topic_memory=raw.get("topic_memory", []),
            confidence=raw.get("confidence", {}),
            last_updated_at=raw.get("last_updated_at", utc_now_iso()),
        )

    def save(self, user_id: str, profile: UserProfile) -> UserProfile:
        compacted = self._compact_profile(profile)
        compacted.last_updated_at = utc_now_iso()
        write_json(self._path(user_id), compacted.to_dict())
        return compacted

    def update(
        self,
        user_id: str,
        *,
        occupation: str | None = None,
        habits: dict[str, Any] | None = None,
        hard_constraints: list[str] | None = None,
        soft_preferences: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> UserProfile:
        profile = self.load(user_id)

        if occupation:
            profile.basic_profile["occupation"] = occupation.strip()
            profile.confidence["basic_profile.occupation"] = 0.9

        if habits:
            profile.interaction_habits.update(habits)

        if hard_constraints:
            old = profile.special_requirements.get("hard_constraints", [])
            profile.special_requirements["hard_constraints"] = _dedupe_keep_order(old + hard_constraints)

        if soft_preferences:
            old = profile.special_requirements.get("soft_preferences", [])
            profile.special_requirements["soft_preferences"] = _dedupe_keep_order(old + soft_preferences)

        if topics:
            profile.topic_memory = _dedupe_keep_order(profile.topic_memory + topics)
            profile.topic_memory = profile.topic_memory[-20:]

        return self.save(user_id, profile)

    def _compact_profile(self, profile: UserProfile) -> UserProfile:
        # 先做一次常规去重和裁剪。
        profile.topic_memory = _dedupe_keep_order(profile.topic_memory)[-20:]
        hard = _dedupe_keep_order(profile.special_requirements.get("hard_constraints", []))
        soft = _dedupe_keep_order(profile.special_requirements.get("soft_preferences", []))
        profile.special_requirements["hard_constraints"] = hard[-20:]
        profile.special_requirements["soft_preferences"] = soft[-20:]

        # 超预算时逐步压缩低优先字段。
        while _estimate_tokens(json.dumps(profile.to_dict(), ensure_ascii=False)) > self.token_limit:
            if len(profile.topic_memory) > 5:
                profile.topic_memory = profile.topic_memory[1:]
                continue
            if len(profile.special_requirements.get("soft_preferences", [])) > 5:
                profile.special_requirements["soft_preferences"] = profile.special_requirements["soft_preferences"][1:]
                continue
            if len(profile.special_requirements.get("hard_constraints", [])) > 5:
                profile.special_requirements["hard_constraints"] = profile.special_requirements["hard_constraints"][1:]
                continue
            # 最后兜底：裁剪长文本值。
            for group in (profile.basic_profile, profile.interaction_habits):
                changed = False
                for k, v in list(group.items()):
                    if isinstance(v, str) and len(v) > 80:
                        group[k] = v[:77] + "..."
                        changed = True
                        break
                if changed:
                    break
            else:
                break

        return profile


def _dedupe_keep_order(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for x in items:
        key = str(x).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out

