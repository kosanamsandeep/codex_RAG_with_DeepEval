from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from rag_practice.domain.models import DocumentChunk, QueryResult
from rag_practice.domain.text_utils import chunk_to_embedding_text, table_to_text
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
        embeddings = self.embedder.embed_texts([chunk_to_embedding_text(c) for c in chunks])
        self.index.upsert(chunks, embeddings)
        return chunks


@dataclass(frozen=True, slots=True)
class QueryRag:
    embedder: Embedder
    index: VectorIndex
    enable_rerank: bool = False
    rerank_multiplier: int = 3
    rerank_weight: float = 0.35

    def execute(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, str] | None = None,
    ) -> Sequence[QueryResult]:
        embedding = self.embedder.embed_query(query)
        pre_k = max(top_k, top_k * self.rerank_multiplier)
        results = list(self.index.query(embedding, top_k=pre_k, filters=filters))
        if not results or not self.enable_rerank:
            return results[:top_k]
        return self._rerank(query, results)[:top_k]

    def _rerank(self, query: str, results: Iterable[QueryResult]) -> list[QueryResult]:
        """
        Lightweight reranker using token overlap with a small weight.

        This improves top-1 precision without introducing new dependencies.
        """
        query_terms = _normalize_terms(query)
        scored: list[tuple[float, QueryResult]] = []
        for r in results:
            text = (r.text or "").strip()
            if not text and r.tables:
                rendered = "\n\n".join(
                    table_to_text(t) for t in r.tables if table_to_text(t)
                ).strip()
                text = rendered or r.chunk_id
            overlap = _overlap_score(query_terms, text)
            # FAISS returns L2 distance (lower is better); invert to score.
            base = -r.score
            combined = (1.0 - self.rerank_weight) * base + self.rerank_weight * overlap
            scored.append((combined, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]


def _normalize_terms(text: str) -> set[str]:
    import re

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    stop = {
        "the", "and", "for", "with", "this", "that", "from", "are", "was", "were",
        "you", "your", "but", "not", "can", "will", "have", "has", "had", "all",
        "any", "page", "source", "chunk", "type", "table", "text",
    }
    return set(t for t in tokens if len(t) > 2 and t not in stop)


def _overlap_score(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0
    terms = _normalize_terms(text)
    if not terms:
        return 0.0
    return len(query_terms & terms) / len(query_terms)
