# RAG Practice

Local practice project for building a RAG app using LangChain, a vector database, and OpenAI multimodal models.
Architecture follows the *Cosmic Python* separation of domain, application, and adapters.

## Features

### Core RAG Capabilities
- **Document Ingestion**: Load and process PDF documents with multimodal support (text + images)
- **Text Chunking**: Intelligent text splitting with configurable chunk size (800 chars) and overlap (120 chars)
- **Vector Database**: FAISS-based vector indexing for semantic search
- **Embedding Generation**: OpenAI embeddings for semantic understanding
- **Retrieval**: Context-aware retrieval with metadata tracking

### Table Support (New - `table_support_rag` branch)
- **Structured Table Extraction**: Detect and extract tables as structured data
- **Table References**: Tables stored as `TableRef` objects with headers and rows
- **Atomic Table Chunks**: Tables remain intact in chunks (not split across boundaries)
- **Queryable Tables**: Tables stored as dicts with column headers for direct queries
- **Metadata Preservation**: Table location, page info, and source tracked

## Architecture

```
src/rag_practice/
├── domain/
│   ├── models.py          # Core data models (Document, Chunk, TableRef, etc.)
│   └── ports.py           # Abstract interfaces
├── adapters/
│   ├── chunking.py        # Text & table chunking logic
│   ├── pdf_loader.py      # PDF parsing and extraction
│   ├── faiss_index.py     # Vector database adapter
│   └── openai_embedder.py # Embedding model adapter
└── application/
    └── use_cases.py       # Business logic (ingest, query)
```

## Setup

1. Create a `.env` file based on `.env.example` and set `OPENAI_API_KEY`:
   ```bash
   OPENAI_API_KEY=sk-...
   ```

2. Install dependencies:
   ```bash
   python -m pip install -e .[dev,eval]
   ```

## Quick Start

### Ingestion
```bash
python scripts/ingest.py
```
Processes PDFs, extracts text/images/tables, and creates vector index.

### Querying
```bash
python scripts/query.py "What is in the table?"
```
Retrieves relevant chunks with semantic search.

### Running Tests
```bash
pytest tests/
```

## Branch Information

### `master` - Baseline Implementation
- Text-only chunking
- Image reference tracking
- Basic vector search

### `table_support_rag` - Table Support Enhancement
Currently in development:
- ✅ Added `TableRef` model for structured table representation
- ✅ Extended `DocumentChunk` and `QueryResult` with `tables` field
- 🔄 Updating `MetadataAwareChunker` to detect and extract tables
- 🔄 Tests for table extraction and storage
- 🔄 Examples showing table vs text differentiation

**Key Changes**:
- **models.py**: New `TableRef` dataclass with headers and rows
- **chunking.py**: Table detection and extraction logic
- **examples/**: Example showing old vs new approach

## Data Models

### TableRef
```python
@dataclass
class TableRef:
    table_id: str                          # Unique identifier
    headers: Sequence[str]                 # Column names
    rows: Sequence[Mapping[str, Any]]      # Rows as dicts
```

### DocumentChunk
```python
@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    tables: Sequence[TableRef] = ()        # NEW: Structured tables
```

## Testing Table Support

See `examples/table_aware_chunking_example.py` for:
- Comparison of old vs new approach
- How tables are extracted and stored
- Query examples with structured data

Run the example:
```bash
python examples/table_aware_chunking_example.py
```

## Next Steps

1. Implement table detection in `chunking.py`
2. Add table extraction tests
3. Integrate with FAISS for table metadata queries
4. Test end-to-end ingestion with table support
5. Merge to master after validation
