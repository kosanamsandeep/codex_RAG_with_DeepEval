from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from rag_practice.adapters.chunking import MetadataAwareChunker
from rag_practice.adapters.faiss_index import FaissInMemoryIndex
from rag_practice.adapters.openai_embedder import OpenAITextEmbedder
from rag_practice.adapters.pdf_loader import PdfDocumentLoader
from rag_practice.application import IngestDocuments


def main() -> None:
    load_dotenv()

    data_dir = Path("data")
    image_dir = Path("data/processed/images")

    loader = PdfDocumentLoader(data_dir=data_dir, image_output_dir=image_dir)
    chunker = MetadataAwareChunker()
    embedder = OpenAITextEmbedder()
    index = FaissInMemoryIndex()

    use_case = IngestDocuments(loader=loader, chunker=chunker, embedder=embedder, index=index)
    chunks = use_case.execute()

    print(f"Ingested {len(chunks)} chunks from PDFs in {data_dir}")
    print(f"FAISS index size: {index._index.ntotal if index._index else 0}")


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing; set it in .env")
    main()
