from pathlib import Path

from rag_practice.adapters.faiss_index import FaissInMemoryIndex
from rag_practice.domain.models import ChunkMetadata, DocumentChunk


def make_chunk(idx: int) -> DocumentChunk:
    metadata = ChunkMetadata(
        source_id="s1",
        page=idx,
        section=None,
        image_refs=[],
        extra={"source_id": "s1", "page": str(idx)},
    )
    return DocumentChunk(chunk_id=f"s1:p{idx}:{idx}", text=f"text {idx}", metadata=metadata)


def test_save_and_load_roundtrip(tmp_path: Path):
    idx_path = tmp_path / "faiss.index"
    meta_path = tmp_path / "chunks.pkl"

    index = FaissInMemoryIndex()
    chunks = [make_chunk(1), make_chunk(2)]
    embeddings = [[0.0, 1.0], [1.0, 0.0]]
    index.upsert(chunks, embeddings)
    index.save(idx_path, meta_path)

    restored = FaissInMemoryIndex()
    restored.load(idx_path, meta_path)

    assert restored._index is not None
    assert restored._index.ntotal == 2
    assert len(restored._chunks) == 2
