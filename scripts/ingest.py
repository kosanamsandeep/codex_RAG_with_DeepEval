from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from rag_practice.adapters.chunking import MetadataAwareChunker
from rag_practice.adapters.faiss_index import FaissInMemoryIndex
from rag_practice.adapters.openai_embedder import OpenAITextEmbedder
from rag_practice.adapters.pdf_loader import PdfDocumentLoader
from rag_practice.application import IngestDocuments
from rag_practice.domain.text_utils import chunk_to_embedding_text


def main() -> None:
    load_dotenv()

    data_dir = Path("data")
    index_dir = Path("data/index")
    image_dir = Path("data/processed/images")
    manifest_path = index_dir / "manifest.json"

    loader = PdfDocumentLoader(data_dir=data_dir, image_output_dir=image_dir)
    chunker = MetadataAwareChunker()
    embedder = OpenAITextEmbedder()
    index = FaissInMemoryIndex()

    current_files = sorted(data_dir.glob("*.pdf"))
    current_state = {
        p.name: {"mtime": p.stat().st_mtime, "size": p.stat().st_size} for p in current_files
    }
    previous_state = {}
    if manifest_path.exists():
        try:
            previous_state = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            previous_state = {}

    removed = set(previous_state.keys()) - set(current_state.keys())
    modified = {
        name
        for name, meta in current_state.items()
        if name in previous_state and previous_state[name] != meta
    }
    full_rebuild = bool(removed or modified)

    if not full_rebuild:
        # Load existing index if present and only ingest new files.
        index.load(index_dir / "faiss.index", index_dir / "chunks.pkl")
        new_files = [p for p in current_files if p.name not in previous_state]
        if not new_files:
            print("No new or changed PDFs. Index is up to date.")
            return
        documents = loader.load_paths(new_files)
        chunks = chunker.chunk(documents)
        embeddings = embedder.embed_texts([chunk_to_embedding_text(c) for c in chunks])
        index.upsert(chunks, embeddings)
    else:
        # Rebuild index if files were removed or modified.
        use_case = IngestDocuments(loader=loader, chunker=chunker, embedder=embedder, index=index)
        chunks = use_case.execute()

    # Save index and chunks to disk
    index.save(
        index_path=index_dir / "faiss.index",
        metadata_path=index_dir / "chunks.pkl"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(current_state, indent=2), encoding="utf-8")

    print(f"Ingested {len(chunks)} chunks from PDFs in {data_dir}")
    print(f"FAISS index size: {index._index.ntotal if index._index else 0}")
    print(f"Saved index to {index_dir / 'faiss.index'}")
    print(f"Saved chunks to {index_dir / 'chunks.pkl'}")
    print(f"Saved manifest to {manifest_path}")


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing; set it in .env")
    main()
