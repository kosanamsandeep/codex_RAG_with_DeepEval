from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

import faiss
import numpy as np
import pickle

from rag_practice.domain.models import DocumentChunk, QueryResult
from rag_practice.domain.ports import VectorIndex


@dataclass
class FaissInMemoryIndex(VectorIndex):
    dim: int | None = None
    _index: faiss.IndexFlatL2 | None = field(init=False, default=None)
    _chunks: list[DocumentChunk] = field(init=False, default_factory=list)

    def upsert(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not chunks:
            return
        vectors = np.array(embeddings, dtype="float32")
        self._init_index_if_needed(vectors.shape[1])
        assert self._index is not None
        self._index.add(vectors)
        self._chunks.extend(chunks)

    def query(
        self,
        embedding: Sequence[float],
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> Sequence[QueryResult]:
        if not self._index or self._index.ntotal == 0:
            return []
        vector = np.array([embedding], dtype="float32")
        distances, indices = self._index.search(vector, top_k)
        results: list[QueryResult] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            chunk = self._chunks[idx]
            if filters and not self._passes_filters(chunk, filters):
                continue
            results.append(
                QueryResult(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    score=float(score),
                    tables=chunk.tables,
                )
            )
        return results

    def _passes_filters(self, chunk: DocumentChunk, filters: Mapping[str, str]) -> bool:
        for key, value in filters.items():
            if chunk.metadata.extra.get(key) != value:
                return False
        return True

    def _init_index_if_needed(self, dim: int) -> None:
        if self._index:
            return
        self._index = faiss.IndexFlatL2(dim)
        self.dim = dim

    def save(self, index_path: Path, metadata_path: Path) -> None:
        if not self._index:
            return
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(index_path))
        with metadata_path.open("wb") as f:
            pickle.dump(self._chunks, f)

    def load(self, index_path: Path, metadata_path: Path) -> None:
        if not index_path.exists() or not metadata_path.exists():
            return
        self._index = faiss.read_index(str(index_path))
        with metadata_path.open("rb") as f:
            self._chunks = pickle.load(f)
        self.dim = self._index.d
