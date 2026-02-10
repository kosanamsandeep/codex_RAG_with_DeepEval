# RAG Pipeline Flow

```
run scripts/query.py
    |
    v
load .env (OPENAI_API_KEY)
    |
    v
build pipelines
  - PdfDocumentLoader
  - MetadataAwareChunker
  - OpenAITextEmbedder (model: text-embedding-3-small)
  - FaissInMemoryIndex
    |
    v
if persistence on (default):
  try load faiss.index + chunks.pkl
else:
  skip load
    |
    v
if index empty or --no-persist:
  IngestDocuments use case
    - loader.load(): read PDFs, extract text, save images, attach page info
    - chunker.chunk(): split text; add metadata (source_id, page, image_refs, extra)
    - embedder.embed_texts(): create embeddings with text-embedding-3-small
    - index.upsert(): store vectors + chunks in FAISS
  if persistence on: save faiss.index + chunks.pkl
    |
    v
QueryRag use case
  - embedder.embed_query(): embed question with text-embedding-3-small
  - index.query(): FAISS search with optional filters
    |
    v
print ranked chunks (score, chunk_id, source_id, page, text)
```

## Metadata usage
- `ChunkMetadata.source_id` and `page` set by `MetadataAwareChunker`.
- `ChunkMetadata.extra` duplicates `source_id` and `page` as strings for filter matching.
- CLI filters:
  - `--source-id` -> `filters["source_id"]`
  - `--page` -> `filters["page"]`
- `FaissInMemoryIndex.query` drops any chunk whose `metadata.extra` key/values don’t match all filters.
- `image_refs` holds extracted image file paths per chunk; currently not used in retrieval, ready for future captioning/multimodal.

## Models used
- Embeddings: OpenAI `text-embedding-3-small` (via `langchain-openai`).
- LLM for answers: none yet; script returns retrieved chunks only. (Can be extended to call an LLM for final generation.)
