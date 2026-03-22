"""Chroma 持久化与 CRUD：建表（Collection）、增删改查。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import chromadb

from .collections import ALL_COLLECTIONS, CollectionName
from .paths import DEFAULT_CHROMA_PERSIST_DIR
from .models import (
    BaseChunkMetadata,
    BugMetadata,
    CppHeaderMetadata,
    KnowledgeDocMetadata,
    PolicyMetadata,
    metadata_to_chroma,
)


class ChromaRepository:
    """
    封装 Chroma ``PersistentClient``，对 ``schema.md`` 中的四个 Collection 提供 CRUD。

    - **Create**: ``add_*`` 方法写入向量与 metadata。
    - **Read**: ``get`` / ``query``。
    - **Update**: ``update_document``（可仅更新 metadata 或正文）。
    - **Delete**: ``delete``。
    """

    def __init__(self, persist_directory: str | Path | None = None) -> None:
        """
        ``persist_directory`` 缺省时使用 ``repository/chroma_db/``（见 ``paths.DEFAULT_CHROMA_PERSIST_DIR``）。
        该目录已在 ``repository/.gitignore`` 中忽略，避免将向量库提交进 Git。
        """
        self._path = (
            Path(persist_directory)
            if persist_directory is not None
            else DEFAULT_CHROMA_PERSIST_DIR
        )
        self._path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._path))

    @property
    def persist_path(self) -> Path:
        """Chroma 持久化根目录。"""
        return self._path

    @property
    def client(self) -> chromadb.ClientAPI:
        return self._client

    def ensure_collections(self) -> dict[str, Any]:
        """创建缺失的 Collection（已存在则直接返回）。"""
        out: dict[str, Any] = {}
        for name in ALL_COLLECTIONS:
            out[name] = self._client.get_or_create_collection(name=name)
        return out

    def get_collection(self, name: CollectionName | str) -> Any:
        key = name.value if isinstance(name, CollectionName) else name
        return self._client.get_or_create_collection(name=key)

    # --- Create ---

    def add_cpp_header(self, document: str, metadata: CppHeaderMetadata) -> str:
        return self._add(CollectionName.CPP_HEADERS, document, metadata)

    def add_bug(self, document: str, metadata: BugMetadata) -> str:
        return self._add(CollectionName.BUGS, document, metadata)

    def add_knowledge_doc(self, document: str, metadata: KnowledgeDocMetadata) -> str:
        return self._add(CollectionName.KNOWLEDGE_DOCS, document, metadata)

    def add_policy(self, document: str, metadata: PolicyMetadata) -> str:
        return self._add(CollectionName.POLICIES, document, metadata)

    def _add(
        self,
        collection: CollectionName,
        document: str,
        metadata: BaseChunkMetadata,
    ) -> str:
        coll = self.get_collection(collection)
        chunk_id = metadata.chunk_id
        coll.add(
            ids=[chunk_id],
            documents=[document],
            metadatas=[metadata_to_chroma(metadata)],
        )
        return chunk_id

    # --- Read ---

    def get(
        self,
        collection: CollectionName | str,
        ids: list[str],
        *,
        include: list[Literal["documents", "metadatas", "embeddings"]] | None = None,
    ) -> dict[str, Any]:
        coll = self.get_collection(collection)
        inc = include or ["documents", "metadatas"]
        return coll.get(ids=ids, include=inc)  # type: ignore[no-any-return]

    def query(
        self,
        collection: CollectionName | str,
        query_texts: list[str],
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        include: list[Literal["documents", "metadatas", "distances", "embeddings"]] | None = None,
    ) -> dict[str, Any]:
        """语义检索（使用 Collection 默认 embedding）。"""
        coll = self.get_collection(collection)
        inc = include or ["documents", "metadatas", "distances"]
        kwargs: dict[str, Any] = {
            "query_texts": query_texts,
            "n_results": n_results,
            "include": inc,
        }
        if where is not None:
            kwargs["where"] = where
        return coll.query(**kwargs)  # type: ignore[no-any-return]

    # --- Update ---

    def update_document(
        self,
        collection: CollectionName | str,
        chunk_id: str,
        *,
        document: str | None = None,
        metadata: BaseChunkMetadata | None = None,
    ) -> None:
        """
        更新单条记录。若只更新 metadata，会从库中读出旧正文再合并 metadata；
        若只更新正文，则保留原 metadata。
        """
        if document is None and metadata is None:
            raise ValueError("document 与 metadata 至少提供一个")

        coll = self.get_collection(collection)
        existing = coll.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not existing["ids"]:
            raise KeyError(f"chunk_id 不存在: {chunk_id!r}")

        old_doc = existing["documents"][0] if existing["documents"] else None
        old_meta = existing["metadatas"][0] if existing["metadatas"] else {}

        new_doc = document if document is not None else old_doc
        if new_doc is None:
            raise KeyError(f"无法解析正文: {chunk_id!r}")

        if metadata is not None:
            merged = {**(old_meta or {}), **metadata_to_chroma(metadata)}
            new_meta = merged
        else:
            new_meta = old_meta

        coll.update(
            ids=[chunk_id],
            documents=[new_doc],
            metadatas=[new_meta],
        )

    # --- Delete ---

    def delete(
        self,
        collection: CollectionName | str,
        ids: list[str],
    ) -> None:
        if not ids:
            return
        coll = self.get_collection(collection)
        coll.delete(ids=ids)


def demo() -> None:
    """本地冒烟：建库、写入、查询、更新、删除。"""
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="chroma_crud_"))
    repo = ChromaRepository(root)
    repo.ensure_collections()

    cid = repo.add_cpp_header(
        "void submitAsync(std::function<void()>); // 异步提交任务",
        CppHeaderMetadata(
            chunk_id="cpp-1",
            file_name="include/async/TaskScheduler.h",
            symbol_name="submitAsync",
            symbol_kind="function",
            doc_year_month="2024-03",
        ),
    )
    print("inserted:", cid)

    g = repo.get(CollectionName.CPP_HEADERS, [cid])
    print("get documents:", g.get("documents"))

    q = repo.query(CollectionName.CPP_HEADERS, ["异步任务"], n_results=1)
    print("query ids:", q.get("ids"))

    repo.update_document(
        CollectionName.CPP_HEADERS,
        cid,
        document="void submitAsync(std::function<void()>); // updated",
    )

    repo.delete(CollectionName.CPP_HEADERS, [cid])
    print("after delete:", repo.get(CollectionName.CPP_HEADERS, [cid])["ids"])


if __name__ == "__main__":
    demo()
