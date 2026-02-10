from rag_practice.adapters.chunking import MetadataAwareChunker
from rag_practice.domain.models import Document, ImageRef, PageContent


def make_doc(text: str) -> Document:
    page = PageContent(page=1, text=text, image_refs=[])
    return Document(source_id="doc1.pdf", pages=[page])


def test_chunking_preserves_metadata():
    chunker = MetadataAwareChunker(chunk_size=20, chunk_overlap=5)
    doc = make_doc("This is a short test document that should be split.")

    chunks = list(chunker.chunk([doc]))

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.metadata.source_id == "doc1.pdf"
        assert chunk.metadata.page == 1
        assert chunk.metadata.extra["source_id"] == "doc1.pdf"
        assert chunk.metadata.extra["page"] == "1"
        assert chunk.metadata.image_refs == []


def test_chunking_keeps_image_refs():
    images = [ImageRef(path="img.png", page=1, caption=None)]
    page = PageContent(page=1, text="Hello world", image_refs=images)
    doc = Document(source_id="doc2.pdf", pages=[page])
    chunker = MetadataAwareChunker(chunk_size=50, chunk_overlap=0)

    chunks = list(chunker.chunk([doc]))

    assert len(chunks) == 1
    assert chunks[0].metadata.image_refs == images
