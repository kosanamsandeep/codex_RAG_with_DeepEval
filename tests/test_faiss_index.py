from rag_practice.adapters.faiss_index import FaissInMemoryIndex
from rag_practice.domain.models import ChunkMetadata, DocumentChunk, QueryResult


def make_chunk(idx: int, source: str, page: int) -> DocumentChunk:
    metadata = ChunkMetadata(
        source_id=source,
        page=page,
        section=None,
        image_refs=[],
        extra={"source_id": source, "page": str(page)},
    )
    return DocumentChunk(
        chunk_id=f"{source}:p{page}:{idx}",
        text=f"chunk {idx} text",
        metadata=metadata,
    )


def test_faiss_upsert_and_query():
    index = FaissInMemoryIndex()
    chunks = [make_chunk(1, "a.pdf", 1), make_chunk(2, "b.pdf", 1)]
    embeddings = [[0.0, 0.0], [1.0, 1.0]]

    index.upsert(chunks, embeddings)
    results = index.query([0.0, 0.0], top_k=2)

    assert len(results) >= 1
    assert isinstance(results[0], QueryResult)
    assert results[0].chunk_id == "a.pdf:p1:1"


def test_faiss_filters_by_metadata():
    index = FaissInMemoryIndex()
    chunks = [make_chunk(1, "a.pdf", 1), make_chunk(2, "b.pdf", 1)]
    embeddings = [[0.0, 0.0], [1.0, 1.0]]
    index.upsert(chunks, embeddings)

    results = index.query([1.0, 1.0], top_k=2, filters={"source_id": "b.pdf"})

    assert len(results) == 1
    assert results[0].metadata.source_id == "b.pdf"
