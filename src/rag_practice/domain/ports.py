from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from rag_practice.domain.models import Document, DocumentChunk, QueryResult


class DocumentLoader(Protocol):
    def load(self) -> Sequence[Document]:
        ...


class Chunker(Protocol):
    def chunk(self, documents: Sequence[Document]) -> Sequence[DocumentChunk]:
        ...


class Embedder(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...

    def embed_query(self, text: str) -> Sequence[float]:
        ...


class VectorIndex(Protocol):
    def upsert(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        ...

    def query(
        self,
        embedding: Sequence[float],
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> Sequence[QueryResult]:
        ...
