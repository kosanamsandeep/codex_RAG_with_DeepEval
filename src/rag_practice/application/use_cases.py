from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from rag_practice.domain.models import DocumentChunk, QueryResult
from rag_practice.domain.ports import Chunker, DocumentLoader, Embedder, VectorIndex


@dataclass(frozen=True, slots=True)
class IngestDocuments:
    loader: DocumentLoader
    chunker: Chunker
    embedder: Embedder
    index: VectorIndex

    def execute(self) -> Sequence[DocumentChunk]:
        documents = self.loader.load()
        chunks = self.chunker.chunk(documents)
        embeddings = self.embedder.embed_texts([c.text for c in chunks])
        self.index.upsert(chunks, embeddings)
        return chunks


@dataclass(frozen=True, slots=True)
class QueryRag:
    embedder: Embedder
    index: VectorIndex

    def execute(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, str] | None = None,
    ) -> Sequence[QueryResult]:
        embedding = self.embedder.embed_query(query)
        return self.index.query(embedding, top_k=top_k, filters=filters)
