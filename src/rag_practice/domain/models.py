from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ImageRef:
    path: str
    page: int
    caption: str | None


@dataclass(frozen=True, slots=True)
class TableRef:
    """Represents a structured table extracted from the document"""
    table_id: str
    headers: Sequence[str]
    rows: Sequence[Mapping[str, Any]]  # Each row is a dict mapping header -> value


@dataclass(frozen=True, slots=True)
class PageContent:
    page: int
    text: str
    image_refs: Sequence[ImageRef]


@dataclass(frozen=True, slots=True)
class Document:
    source_id: str
    pages: Sequence[PageContent]


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    source_id: str
    page: int
    section: str | None
    image_refs: Sequence[ImageRef]
    extra: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    tables: Sequence[TableRef] = ()  # NEW: Tables extracted from this chunk


@dataclass(frozen=True, slots=True)
class QueryResult:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    score: float
    tables: Sequence[TableRef] = ()  # NEW: Tables in the result
