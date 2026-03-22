"""持久化与 Chroma 向量库 CRUD。"""

from .chroma_crud import ChromaRepository
from .collections import ALL_COLLECTIONS, CollectionName
from .models import (
    BaseChunkMetadata,
    BugMetadata,
    CppHeaderMetadata,
    KnowledgeDocMetadata,
    PolicyMetadata,
    metadata_to_chroma,
)
from .paths import DEFAULT_CHROMA_PERSIST_DIR, REPOSITORY_ROOT

__all__ = [
    "ALL_COLLECTIONS",
    "CollectionName",
    "ChromaRepository",
    "DEFAULT_CHROMA_PERSIST_DIR",
    "REPOSITORY_ROOT",
    "BaseChunkMetadata",
    "CppHeaderMetadata",
    "BugMetadata",
    "KnowledgeDocMetadata",
    "PolicyMetadata",
    "metadata_to_chroma",
]
