"""向量库 metadata 的 Pydantic 模型，与 ``repository/schema.md`` 对齐。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------


class BaseChunkMetadata(BaseModel):
    """schema.md「通用约定」+ 溯源字段。"""

    model_config = ConfigDict(extra="allow")

    doc_id: str | None = None
    chunk_id: str = Field(..., description="集合内主键，对应 Chroma ids")
    parent_chunk_id: str | None = None
    chunk_index: int | None = None
    title: str | None = None
    topic: str | None = None
    record_date: str | None = None
    domain: str | None = None
    updated_at: str | None = None
    source_uri: str | None = None
    data_source: str | None = None


class CppHeaderMetadata(BaseChunkMetadata):
    """``cpp_headers`` collection。"""

    file_name: str
    symbol_name: str
    symbol_kind: str | None = None
    signature: str | None = None
    doc_year_month: str | None = None


class BugMetadata(BaseChunkMetadata):
    """``bugs`` collection（与 schema.md 字段一致）。"""

    bug_id: str
    created_at: str | None = None
    resolved_at: str | None = None
    status: str | None = None
    component: str | None = None
    module: str | None = None
    root_cause: str | None = None
    related_bug_ids: list[str] | None = None
    text_role: str | None = Field(
        default=None,
        description="拆条时：test / dev / merged",
    )

    @field_validator("related_bug_ids", mode="before")
    @classmethod
    def _parse_related(cls, v: Any) -> Any:
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


class KnowledgeDocMetadata(BaseChunkMetadata):
    """``knowledge_docs`` collection（培训 + 设计）。"""

    file_name: str | None = None
    section_title: str | None = None

    @model_validator(mode="after")
    def _file_or_topic(self) -> KnowledgeDocMetadata:
        if not self.file_name and not self.topic:
            raise ValueError("file_name 与 topic 至少填写一项")
        return self


class PolicyMetadata(BaseChunkMetadata):
    """``policies`` collection。"""

    file_name: str | None = None
    section_title: str | None = Field(
        default=None,
        description="条款/小节标题，可与正文分离存放便于展示",
    )
    issuer: str | None = None
    clause_id: str | None = None

    @model_validator(mode="after")
    def _file_or_topic(self) -> PolicyMetadata:
        if not self.file_name and not self.topic:
            raise ValueError("file_name 与 topic 至少填写一项")
        return self


def metadata_to_chroma(meta: BaseModel) -> dict[str, Any]:
    """
    Chroma metadata 仅支持标量；``None`` 省略；``list``/复杂结构 JSON 字符串化。
    """
    raw = meta.model_dump(exclude_none=True)
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, (list, dict)):
            out[key] = json.dumps(value, ensure_ascii=False)
        else:
            out[key] = value
    return out


def chroma_to_bug_related_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        return None
