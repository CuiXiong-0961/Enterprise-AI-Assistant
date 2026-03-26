"""长时记忆-窗口摘要模块：每 50 轮压缩并写入用户专属向量库。"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import chromadb

from .constants import VECTOR_DB_DIR, WINDOW_KEEP_MAX, WINDOW_META_DIR, WINDOW_TURNS
from .schemas import MemoryWindow, TurnRecord, utc_now_iso
from .storage import ensure_memory_dirs, read_json, write_json


class ConversationWindowStore:
    """管理用户窗口摘要的生成、向量入库、检索与淘汰。"""

    def __init__(self, window_turns: int = WINDOW_TURNS, keep_max: int = WINDOW_KEEP_MAX) -> None:
        ensure_memory_dirs()
        self.window_turns = window_turns
        self.keep_max = keep_max
        self.client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    def _meta_path(self, user_id: str) -> Path:
        return WINDOW_META_DIR / f"{user_id}.json"

    def _collection_name(self, user_id: str) -> str:
        return f"user_{user_id}_memory_windows"

    def _load_meta(self, user_id: str) -> dict[str, Any]:
        return read_json(self._meta_path(user_id), default={"turn_count": 0, "windows": []})

    def _save_meta(self, user_id: str, meta: dict[str, Any]) -> None:
        write_json(self._meta_path(user_id), meta)

    def append_turn_and_maybe_compress(self, user_id: str, turn: TurnRecord) -> MemoryWindow | None:
        meta = self._load_meta(user_id)
        turn_count = int(meta.get("turn_count", 0)) + 1
        meta["turn_count"] = turn_count

        pending = meta.get("pending_turns", [])
        pending.append(turn.to_dict())
        meta["pending_turns"] = pending[-self.window_turns :]

        out_window: MemoryWindow | None = None
        if turn_count % self.window_turns == 0 and len(meta["pending_turns"]) >= self.window_turns:
            out_window = self._compress_window(user_id, meta["pending_turns"])
            windows = meta.get("windows", [])
            windows.append(out_window.to_dict())
            windows = windows[-self.keep_max :]
            meta["windows"] = windows
            meta["pending_turns"] = []
            self._sync_collection_to_meta(user_id, windows)

        self._save_meta(user_id, meta)
        return out_window

    def retrieve(self, user_id: str, query: str, top_k: int = 2) -> list[dict[str, Any]]:
        coll = self.client.get_or_create_collection(name=self._collection_name(user_id))
        count = coll.count()
        if count == 0:
            return []
        res = coll.query(query_texts=[query], n_results=max(1, top_k), include=["documents", "metadatas", "distances"])
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        out: list[dict[str, Any]] = []
        for i in range(min(len(docs), len(metas), len(dists))):
            out.append(
                {
                    "summary": docs[i],
                    "metadata": metas[i],
                    "distance": dists[i],
                }
            )
        return out

    def _compress_window(self, user_id: str, turns_raw: list[dict[str, Any]]) -> MemoryWindow:
        turns = [
            TurnRecord(
                turn_id=int(t["turn_id"]),
                timestamp=str(t["timestamp"]),
                user_message=str(t["user_message"]),
                assistant_message=str(t["assistant_message"]),
                intent=t.get("intent"),
            )
            for t in turns_raw
        ]
        start_turn = turns[0].turn_id
        end_turn = turns[-1].turn_id
        win_no = (end_turn // self.window_turns)
        window_id = f"W{win_no:04d}"
        time_range = f"{turns[0].timestamp} ~ {turns[-1].timestamp}"
        topics = self._extract_topics(turns)
        summary = self._build_summary(turns, topics, window_id, time_range)
        window = MemoryWindow(
            window_id=window_id,
            user_id=user_id,
            start_turn_id=start_turn,
            end_turn_id=end_turn,
            created_at=utc_now_iso(),
            time_range=time_range,
            summary=summary,
            topics=topics,
        )
        return window

    def _sync_collection_to_meta(self, user_id: str, windows: list[dict[str, Any]]) -> None:
        coll = self.client.get_or_create_collection(name=self._collection_name(user_id))
        old = coll.get(include=[])
        old_ids = old.get("ids", [])
        if old_ids:
            coll.delete(ids=old_ids)

        if not windows:
            return

        ids = [w["window_id"] for w in windows]
        docs = [w["summary"] for w in windows]
        metadatas = [
            {
                "user_id": user_id,
                "window_id": w["window_id"],
                "start_turn_id": w["start_turn_id"],
                "end_turn_id": w["end_turn_id"],
                "created_at": w["created_at"],
                "time_range": w["time_range"],
            }
            for w in windows
        ]
        # 通过固定 window_id 覆盖写入，保证最多保留 keep_max 个窗口。
        coll.add(ids=ids, documents=docs, metadatas=metadatas)

    def _build_summary(
        self,
        turns: list[TurnRecord],
        topics: list[str],
        window_id: str,
        time_range: str,
    ) -> str:
        parts: list[str] = []
        parts.append(f"窗口编号: {window_id}")
        parts.append(f"时间范围: {time_range}")
        parts.append(f"核心主题: {', '.join(topics) if topics else '无明显主题'}")
        parts.append("关键对话摘录:")
        for t in turns[-6:]:
            user = t.user_message.replace("\n", " ").strip()[:120]
            assistant = t.assistant_message.replace("\n", " ").strip()[:120]
            parts.append(f"- 用户: {user}")
            parts.append(f"  助手: {assistant}")
        return "\n".join(parts)

    def _extract_topics(self, turns: list[TurnRecord]) -> list[str]:
        bag: list[str] = []
        for t in turns:
            text = f"{t.user_message} {t.assistant_message}"
            for token in _simple_tokens(text):
                bag.append(token)
        counts = Counter(bag)
        return [w for w, _ in counts.most_common(5)]


def _simple_tokens(text: str) -> list[str]:
    words: list[str] = []
    buff: list[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"_", "-"}:
            buff.append(ch.lower())
        else:
            if buff:
                token = "".join(buff)
                if len(token) >= 3:
                    words.append(token)
                buff = []
    if buff:
        token = "".join(buff)
        if len(token) >= 3:
            words.append(token)
    return words

