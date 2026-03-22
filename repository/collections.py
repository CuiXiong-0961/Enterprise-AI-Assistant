"""Chroma Collection 名称，与 ``schema.md`` 一致。"""

from __future__ import annotations

from enum import Enum


class CollectionName(str, Enum):
    CPP_HEADERS = "cpp_headers"
    BUGS = "bugs"
    KNOWLEDGE_DOCS = "knowledge_docs"
    POLICIES = "policies"


ALL_COLLECTIONS: tuple[str, ...] = tuple(c.value for c in CollectionName)
