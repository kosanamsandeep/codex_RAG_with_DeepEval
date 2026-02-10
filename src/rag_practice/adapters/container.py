from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from rag_practice.adapters.chunking import MetadataAwareChunker
from rag_practice.adapters.faiss_index import FaissInMemoryIndex
from rag_practice.adapters.openai_embedder import OpenAITextEmbedder
from rag_practice.adapters.pdf_loader import PdfDocumentLoader
from rag_practice.application import IngestDocuments, QueryRag


def load_env() -> None:
    # Side effect isolated for reuse across scripts.
    load_dotenv()


def build_ingest_pipeline(
    data_dir: str | Path = "data",
    image_dir: str | Path = "data/processed/images",
) -> IngestDocuments:
    loader = PdfDocumentLoader(data_dir=Path(data_dir), image_output_dir=Path(image_dir))
    chunker = MetadataAwareChunker()
    embedder = OpenAITextEmbedder()
    index = FaissInMemoryIndex()
    return IngestDocuments(loader=loader, chunker=chunker, embedder=embedder, index=index)


def build_query_pipeline(index: FaissInMemoryIndex) -> QueryRag:
    embedder = OpenAITextEmbedder()
    return QueryRag(embedder=embedder, index=index)
