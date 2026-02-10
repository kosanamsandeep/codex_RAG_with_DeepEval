# RAG End to End Workflow Sample Implementation

A comprehensive Retrieval-Augmented Generation (RAG) system built with LangChain, FAISS, and OpenAI. Features multimodal document processing (text, tables, images), semantic search, and an interactive chat interface with cited answers.

**Architecture**: Cosmic Python (clean separation of domain, adapters, and application logic)

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Data Handling](#data-handling)
4. [Setup](#setup)
5. [Quick Start](#quick-start)
6. [API & Scripts](#api--scripts)
7. [Evaluation](#evaluation)
8. [Chat UI](#chat-ui)
9. [Project Status](#project-status)

---

## Features

### Core RAG Capabilities
- **Multimodal Document Ingestion**: Load PDFs, extract text, tables, and images
- **Intelligent Text Chunking**: Recursive character splitting with configurable chunk size (800 chars) and overlap (120 chars)
- **Structured Table Extraction**: Detect and extract tables as queryable structured data (not plain text)
- **Image Extraction & Tracking**: Extract images from PDFs, track references with page numbers
- **FAISS Vector Database**: Fast semantic indexing and similarity search
- **OpenAI Embeddings**: High-quality semantic representations
- **Cited Answers**: Chat interface with inline citations linked to source chunks

### Advanced Features
- **Table Support**: Tables stored as `TableRef` objects with headers and row-based column mappings
- **Metadata Filtering**: Query with filters on source document, page range, and content type
- **Similarity Thresholding**: Filter retrieved results by FAISS distance score
- **Retrieval Evaluation**: Precision@k and Recall@k metrics using deepeval
- **Chat History**: Multi-turn conversation with maintained context

---

## Architecture

```
src/rag_practice/
├── domain/
│   ├── models.py          # Core dataclasses (Document, Chunk, TableRef, QueryResult)
│   └── ports.py           # Abstract interfaces (VectorIndex, Embedder)
├── adapters/
│   ├── chunking.py        # Text splitting & table extraction logic
│   ├── pdf_loader.py      # PDF parsing with text, table, image extraction
│   ├── faiss_index.py     # FAISS vector database wrapper
│   ├── openai_embedder.py # OpenAI embedding adapter
│   └── container.py       # Dependency injection / service building
└── application/
    └── use_cases.py       # Business logic (IngestUseCase, QueryUseCase)

scripts/
├── ingest.py              # CLI: Load PDFs, chunk, embed, index
├── query.py               # CLI: Query the index and retrieve results
├── generate_eval_set.py   # Generate evaluation queries/qrels from chunks
├── eval_retriever_deepeval.py  # Evaluate retriever performance
└── chat_ui_streamlit.py   # Interactive chat UI with citations

tests/
├── test_chunking.py
├── test_table_models.py
├── test_table_extraction_phase2.py
└── ... (additional test files)

data/
├── processed/             # PDFs and extracted images
├── index/
│   ├── faiss.index        # Vector index
│   ├── chunks.pkl         # Serialized chunks metadata
│   └── eval/
│       ├── eval_queries.jsonl   # Evaluation queries
│       └── eval_qrels.jsonl     # Ground truth qrels
```

---

## Data Handling

### Text Data

**Processing Flow**:
```
PDF → extract text per page → detect tables & separate text sections → 
chunk text sections recursively → embed → store in FAISS
```

**Implementation** (`chunking.py`):
- `MetadataAwareChunker.chunk()`: Main entry point
- `_chunk_document()`: Process each page
- `RecursiveCharacterTextSplitter`: Split on `\n\n`, `\n`, ` `, `` (character-level fallback)
- **Chunk Parameters**:
  - Size: 800 characters
  - Overlap: 120 characters
- **Metadata Per Chunk**:
  - `source_id`: Document filename
  - `page`: Page number
  - `section`: Section name (if applicable)
  - `chunk_type`: "text" or "table"
  - `image_refs`: References to images on that page

**Example Text Chunk**:
```json
{
  "chunk_id": "basic-text.pdf:p1:1",
  "text": "This is the first paragraph of text on page 1...",
  "metadata": {
    "source_id": "basic-text.pdf",
    "page": 1,
    "section": null,
    "image_refs": [],
    "extra": {
      "source_id": "basic-text.pdf",
      "page": "1",
      "chunk_type": "text"
    }
  },
  "tables": []
}
```

---

### Tabular Data

**Processing Flow**:
```
PDF text → detect table patterns (multi-space delimiters) → 
extract table lines → parse headers/rows → create TableRef objects → 
store as dedicated chunks (no plain text)
```

**Detection** (`chunking.py`):
- `_extract_tables_from_text()`: Separates text sections from table regions
- `_is_potential_table_line()`: Heuristics:
  - 2+ words per line
  - Most words < 100 characters (filters long prose)
  - Line length > 10 characters
- `_extract_table_lines()`: Collect consecutive table rows
- `_smart_split_table_line()`: Parse columns
  - First tries multi-space splits (common in PDFs)
  - Falls back to single-space splits
- `_parse_table()`: Create `TableRef` with headers and row dicts

**TableRef Structure**:
```python
@dataclass(frozen=True, slots=True)
class TableRef:
    table_id: str                          # Unique ID (e.g., "doc.pdf:p2:table_1")
    headers: Sequence[str]                 # Column names: ["Name", "Age", "City"]
    rows: Sequence[Mapping[str, Any]]      # List of dicts: [{"Name": "Alice", "Age": 30, ...}]
```

**Example Table Chunk**:
```json
{
  "chunk_id": "image-doc.pdf:p3:table_1",
  "text": "",  # Empty for table-only chunks
  "metadata": {
    "source_id": "image-doc.pdf",
    "page": 3,
    "section": null,
    "image_refs": [],
    "extra": {
      "source_id": "image-doc.pdf",
      "page": "3",
      "chunk_type": "table"
    }
  },
  "tables": [
    {
      "table_id": "image-doc.pdf:p3:table_1",
      "headers": ["Product", "Q1", "Q2", "Q3", "Q4"],
      "rows": [
        {"Product": "Widget A", "Q1": "100", "Q2": "120", "Q3": "140", "Q4": "160"},
        {"Product": "Widget B", "Q1": "80", "Q2": "95", "Q3": "110", "Q4": "125"}
      ]
    }
  ]
}
```

**Advantages**:
- ✅ Tables not split across chunks (atomic)
- ✅ Queryable structure (can filter by column values)
- ✅ No overlap duplication within tables
- ✅ Distinguishable from text in results

---

### Image Data

**Processing Flow**:
```
PDF → extract images per page → save to data/processed/images/ → 
create ImageRef with page & caption → attach to chunks
```

**Implementation** (`pdf_loader.py`):
- `PdfDocumentLoader.load()`: Main entry point
- Extract text + images per page
- Create `ImageRef` for each image: `(path, page, caption)`
- Attach `ImageRef` list to `PageContent`

**ImageRef Structure**:
```python
@dataclass(frozen=True, slots=True)
class ImageRef:
    path: str              # Relative path: "data/processed/images/doc_p1_img0.png"
    page: int              # Page number where image appears
    caption: str | None    # Optional caption text
```

**Metadata in Chunks**:
```json
{
  "chunk_id": "image-doc.pdf:p2:1",
  "text": "...",
  "metadata": {
    "source_id": "image-doc.pdf",
    "page": 2,
    "image_refs": [
      {"path": "data/processed/images/image-doc_p2_img0.png", "page": 2, "caption": null}
    ],
    "extra": {...}
  }
}
```

**Usage in Queries**:
- Chunks with image references are retrieved normally
- User can view extracted images via links in the chat UI
- Future enhancement: Use multimodal embeddings (CLIP) to embed images

---

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key

### Installation

1. Clone and enter the repo:
```bash
git clone <repo>
cd codex_rag_workspace
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev,eval]"
```

4. Create `.env` file:
```bash
OPENAI_API_KEY=sk-...
```

5. Add PDFs to ingest:
```bash
# Copy PDFs to data/processed/
cp /path/to/documents/*.pdf data/processed/
```

---

## Quick Start

### 1. Ingest Documents
```bash
python scripts/ingest.py
```
**Output**:
- `data/index/faiss.index` — Vector index
- `data/index/chunks.pkl` — Serialized chunks with metadata
- `data/processed/images/` — Extracted images

**What happens**:
- Loads all PDFs from `data/processed/*.pdf`
- Extracts text, tables, images
- Splits text into chunks (800 chars, 120 overlap)
- Detects and extracts tables as structured data
- Embeds all chunks with OpenAI
- Stores vectors in FAISS

### 2. Query (CLI)
```bash
# Basic query
python scripts/query.py "What is in the table?"

# With options
python scripts/query.py "Your question" --top-k 5 --source-id basic-text.pdf
```

**Output**: Retrieved chunks with similarity scores

### 3. Chat UI
```bash
streamlit run scripts/chat_ui_streamlit.py
```

**Features**:
- Chat interface with history
- Retrieves top-k relevant chunks
- Generates answers with OpenAI GPT-4
- Shows inline citations [1], [2], etc.
- Click citations to expand and see:
  - Source document and page
  - Chunk text
  - Similarity score
  - Content type (text or table)

### 4. Evaluation
```bash
# Generate evaluation set from persisted chunks
python scripts/generate_eval_set.py --metadata data/index/chunks.pkl --out-dir data/index/eval

# Run evaluation (precision@k, recall@k)
python scripts/eval_retriever_deepeval.py \
  --queries data/index/eval/eval_queries.jsonl \
  --qrels data/index/eval/eval_qrels.jsonl
```

---

## API & Scripts

### `src/rag_practice/domain/models.py`

Core data models (frozen dataclasses):

- **`ImageRef`**: Image reference with path, page, caption
- **`TableRef`**: Structured table with headers and row-based column mappings
- **`PageContent`**: Page text, page number, image references
- **`Document`**: Document metadata and pages
- **`ChunkMetadata`**: Chunk source, page, section, images, extra fields
- **`DocumentChunk`**: Chunk with text, metadata, and optional tables
- **`QueryResult`**: Result from vector search with score

### `src/rag_practice/adapters/chunking.py`

**`MetadataAwareChunker`** (dataclass):
- `chunk(documents: Sequence[Document]) -> Sequence[DocumentChunk]`
  - Main entry point; chunks all documents
- `_chunk_document(document, splitter) -> Iterable[DocumentChunk]`
  - Process a single document: extract tables, chunk text sections, create chunks
- `_extract_tables_from_text(text, source_id, page_num) -> tuple[list[str], list[TableRef]]`
  - Detect and extract tables; return text sections + table objects
- `_is_potential_table_line(line) -> bool`
  - Heuristic to identify table lines (multi-word, reasonable word length)
- `_extract_table_lines(lines, start_idx) -> list[str]`
  - Collect consecutive table rows
- `_smart_split_table_line(line) -> list[str]`
  - Parse columns: try multi-space first, then single-space
- `_parse_table(headers, rows, source_id, page_num, table_idx) -> TableRef`
  - Convert parsed lines to structured TableRef

### `src/rag_practice/adapters/pdf_loader.py`

**`PdfDocumentLoader`** (dataclass):
- `load(pdf_paths: Sequence[Path]) -> Sequence[Document]`
  - Load PDFs; extract text, tables, images per page
- Returns `Document` objects with pages, text, images

### `src/rag_practice/adapters/faiss_index.py`

**`FaissInMemoryIndex`** (dataclass):
- `upsert(chunks, embeddings) -> None`
  - Add vectors to index
- `query(embedding, top_k, filters) -> Sequence[QueryResult]`
  - Search and retrieve; supports metadata filtering
- `save(index_path, metadata_path) -> None`
  - Persist index and chunks
- `load(index_path, metadata_path) -> None`
  - Restore index and chunks

### `src/rag_practice/adapters/openai_embedder.py`

**`OpenAIEmbedder`** (dataclass):
- `embed(texts: Sequence[str]) -> Sequence[Sequence[float]]`
  - Generate embeddings via OpenAI API

### `src/rag_practice/application/use_cases.py`

**`IngestUseCase`**:
- `execute() -> None`
  - Load documents → chunk → embed → index

**`QueryUseCase`**:
- `execute(question, top_k, filters) -> Sequence[QueryResult]`
  - Embed question → search FAISS → return results

---

## Evaluation

### Generate Evaluation Set

```bash
python scripts/generate_eval_set.py \
  --metadata data/index/chunks.pkl \
  --out-dir data/index/eval \
  --sample-rate 1.0 \
  --min-len 10
```

**Generates**:
- `eval_queries.jsonl`: Each chunk becomes a query
  - Format: `{"query_id": "<chunk_id>", "query": "<first line of chunk>"}`
- `eval_qrels.jsonl`: Ground truth (the chunk itself is relevant)
  - Format: `{"query_id": "<chunk_id>", "relevant_ids": ["<chunk_id>"]}`

### Run Evaluation

```bash
python scripts/eval_retriever_deepeval.py \
  --queries data/index/eval/eval_queries.jsonl \
  --qrels data/index/eval/eval_qrels.jsonl
```

**Metrics**:
- `p@1`: Precision at top-1 (is the #1 result relevant?)
- `r@1`: Recall at top-1 (is relevant result in top-1?)
- `p@3`, `r@3`, `p@5`, `r@5`: Same for k=3 and k=5

**Example Output**:
```json
{
  "p@1": 1.0,
  "r@1": 1.0,
  "p@3": 0.3333,
  "r@3": 1.0,
  "p@5": 0.2,
  "r@5": 1.0
}
```

**Interpretation**:
- High recall = relevant chunks are retrieved
- Lower precision at higher k = many non-relevant items in results
- Solutions: Increase similarity threshold, use reranking, refine embeddings

---

## Chat UI

### Run the UI

```bash
streamlit run scripts/chat_ui_streamlit.py
```

Open `http://localhost:8501` in your browser.

### Features

**Chat Interface**:
- Multi-turn conversation with history
- Context maintained across turns
- User messages and assistant responses

**Cited Answers**:
- Answers include inline citations: [1], [2], etc.
- Each citation links to a retrieved chunk

**Citation Details** (click to expand):
- Source document and page
- Chunk text (excerpt)
- Similarity score
- Content type (text or table)
- Metadata (section, image references)

**Retrieval Settings** (sidebar):
- **Number of sources** (top-k): 1–10 (default: 3)
- **Force fresh ingest**: Checkbox to skip persisted index
- **Reload Index**: Button to reload FAISS index
- **Show raw chunks**: Debug view of retrieved chunks

**Metadata-Based Filtering** (sidebar):
- Filter by source document (optional)
- Filter by page range (optional)
- Filter by chunk type (text vs. table) (optional)

**Similarity Thresholding**:
- Configurable FAISS distance threshold
- Only show results below threshold (default: no filter)

### Example Workflow

1. User enters: "What is the total Q1 revenue?"
2. Streamlit embeds the question
3. FAISS retrieves top-3 similar chunks
4. GPT-4 reads chunks and generates answer:
   - "Based on the documents, total Q1 revenue was $500K [1]."
5. Click [1] to see:
   - Source: "quarterly-report.pdf"
   - Page: 5
   - Text: "Q1 Revenue: $500K total..."
   - Score: 0.876

---

## Project Status

### ✅ Completed (Phase 1 & 2)

- [x] Core RAG pipeline (load → chunk → embed → index)
- [x] Text chunking with configurable parameters
- [x] Table detection and structured extraction
- [x] Image extraction and tracking
- [x] FAISS vector search with metadata filtering
- [x] OpenAI embeddings integration
- [x] CLI query interface
- [x] Comprehensive test suite (11+ tests)
- [x] Streamlit chat UI with citations
- [x] Evaluation framework (precision@k, recall@k)
- [x] Documentation and examples

### 🔄 In Development / Future

- [ ] PDF viewer with page highlighting in chat UI
- [ ] Multi-modal embeddings (CLIP for images)
- [ ] Table-specific embeddings and querying
- [ ] Reranking (e.g., with CrossEncoder)
- [ ] Caching embeddings for large corpora
- [ ] Batch query evaluation
- [ ] Production deployment (Docker, API server)

---

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_table_models.py -v
```

With coverage:
```bash
pytest tests/ --cov=src/rag_practice
```

---

## Troubleshooting

### OPENAI_API_KEY not set
- Create `.env` file in repo root with `OPENAI_API_KEY=sk-...`
- Run `python -m dotenv list` to verify

### No documents found
- Ensure PDFs are in `data/processed/*.pdf`
- Run `python scripts/ingest.py` first

### Poor retrieval results
- Check similarity scores in chat UI (should be low FAISS distance)
- Increase `--top-k` in query
- Run evaluation to measure precision/recall
- Consider adding more documents or adjusting chunk size

### Streamlit errors
- Install: `pip install streamlit langchain-openai`
- Clear cache: `rm -rf ~/.streamlit/`
- Restart: `streamlit run scripts/chat_ui_streamlit.py --logger.level=debug`

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `pytest tests/`
3. Commit with clear messages: `git commit -m "feat: add new feature"`
4. Push and open a PR

---

## License

MIT

