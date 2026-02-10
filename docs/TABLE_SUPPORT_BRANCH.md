# Table Support Enhancement - Development Notes

**Branch**: `table_support_rag`  
**Status**: In Development  
**Goal**: Add structured table extraction and retrieval to RAG system

## Overview

This branch extends the RAG system to handle tabular data as first-class citizens rather than plain text. Tables are extracted as structured data with headers and rows, enabling:

- **Semantic preservation**: Tables stay intact (not split across chunks)
- **Structured queries**: Direct access to table data via column headers
- **Better retrieval**: Distinguish between narrative text and tabular data
- **Export capability**: Easy conversion to CSV/JSON

## What Changed

### 1. Domain Models (`src/rag_practice/domain/models.py`)

**Added `TableRef` class**:
```python
@dataclass(frozen=True, slots=True)
class TableRef:
    """Represents a structured table extracted from the document"""
    table_id: str                          # e.g., "basic-text.pdf:p1:table1"
    headers: Sequence[str]                 # Column names
    rows: Sequence[Mapping[str, Any]]      # Each row as dict with header -> value
```

**Extended `DocumentChunk`**:
```python
@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    tables: Sequence[TableRef] = ()  # NEW: Embedded tables
```

**Extended `QueryResult`**:
```python
@dataclass(frozen=True, slots=True)
class QueryResult:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    score: float
    tables: Sequence[TableRef] = ()  # NEW: Tables in results
```

### 2. Examples (`examples/table_aware_chunking_example.py`)

Demonstrates:
- **OLD approach**: Tables as plain text (split across chunks, hard to query)
- **NEW approach**: Tables as structured data (intact, queryable)
- **Retrieval benefits**: Shows how structured queries work vs semantic search

Run it:
```bash
python examples/table_aware_chunking_example.py
```

## Testing

### Unit Tests Needed

Create `tests/test_table_extraction.py`:
```python
def test_table_extraction_from_text():
    """Test detecting and extracting tables from PDF text"""
    pass

def test_table_chunk_creation():
    """Test creating TableRef chunks"""
    pass

def test_table_metadata_preservation():
    """Test that table metadata is preserved"""
    pass
```

### Integration Tests Needed

Create `tests/test_table_ingestion.py`:
```python
def test_end_to_end_table_ingestion():
    """Test full pipeline: PDF -> extract -> store -> retrieve"""
    pass

def test_table_retrieval_with_semantic_search():
    """Test retrieving tables via semantic search"""
    pass
```

## Implementation Checklist

### Phase 1: Data Model (✅ DONE)
- ✅ Create `TableRef` dataclass
- ✅ Add `tables` field to `DocumentChunk`
- ✅ Add `tables` field to `QueryResult`
- ✅ Create example demonstrating new model

### Phase 2: Table Detection (🔄 IN PROGRESS)
- ⏳ Detect table patterns in PDF text
- ⏳ Extract headers and rows
- ⏳ Handle multi-line headers
- ⏳ Handle merged cells (if applicable)

### Phase 3: Chunking Logic (🔄 TO DO)
- ⏳ Update `MetadataAwareChunker` to skip tables in text
- ⏳ Create separate `TableRef` chunks
- ⏳ Remove table text from body chunks
- ⏳ Preserve chunk ordering and relationships

### Phase 4: Testing (🔄 TO DO)
- ⏳ Unit tests for table detection
- ⏳ Unit tests for table extraction
- ⏳ Integration tests with FAISS
- ⏳ End-to-end tests with sample PDFs

### Phase 5: Integration (🔄 TO DO)
- ⏳ Update ingest script for table support
- ⏳ Update query script to handle table chunks
- ⏳ Update embedding strategy for tables
- ⏳ Validate with existing test PDFs

## Key Design Decisions

### 1. Tables as Separate Chunks
Instead of mixing tables with text, create dedicated table chunks:
```
CHUNK #1: Text before table (no table data)
CHUNK #2: The table itself (pure structure)
CHUNK #3: Text after table (no table data)
```

**Rationale**: 
- Prevents table splitting
- Cleaner semantic representation
- Easier to apply different embedding strategies

### 2. Rows as Dictionaries
Store rows as `Dict[header, value]` not just lists:
```python
# NEW: Query by column name
table.rows[0]["Cost"]  # Returns: "500"

# OLD: Query by position (fragile)
text.split()[5]  # Depends on exact formatting
```

**Rationale**:
- Self-documenting (knows what each value means)
- Resilient to formatting changes
- Supports direct SQL-like queries

### 3. Table ID Format
`{source_id}:{page}:table{index}` (e.g., `basic-text.pdf:p1:table1`)

**Rationale**:
- Globally unique
- Traceable to source
- Human-readable

## Backward Compatibility

Changes are **backward compatible**:
- `tables=()` is the default (empty tuple)
- Existing chunks work without table support
- No breaking changes to existing methods
- Can migrate data incrementally

## Testing with Sample PDFs

### Current Test PDFs
- `data/basic-text.pdf` - Contains simple table (Header 1-3, 2 rows)
- `data/image-doc.pdf` - Image-heavy, no tables

### To Test Table Support
```bash
# Generate chunks with table extraction
python scripts/ingest.py

# Show chunks with tables
python examples/table_aware_chunking_example.py

# Query table data
python scripts/query.py "What is in the table?"
```

## Metrics for Success

### Functional
- ✅ Tables extracted correctly from PDF
- ✅ Table structure preserved (headers, rows)
- ✅ Chunks contain `TableRef` objects
- ✅ Can query tables by column name

### Performance
- ⏳ No performance degradation vs text-only
- ⏳ Embedding generation same or faster

### Quality
- ⏳ 100% of tables detected and extracted
- ⏳ 100% of headers and rows captured accurately
- ⏳ All tests passing

## Next Phase

Once Phase 5 (Integration) is complete:
1. Create PR from `table_support_rag` to `master`
2. Run full test suite
3. Validate with user feedback
4. Merge to master

## References

- **Models**: [src/rag_practice/domain/models.py](../src/rag_practice/domain/models.py)
- **Example**: [examples/table_aware_chunking_example.py](../examples/table_aware_chunking_example.py)
- **Main README**: [README.md](../README.md)
