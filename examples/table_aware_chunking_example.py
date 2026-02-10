"""
Example: How Table-Aware Chunking Differentiates Tables from Text
==================================================================

This shows the difference between:
1. OLD: Treating tables as plain text (gets split across chunks)
2. NEW: Extracting tables as structured data (tables stay intact)
"""

from rag_practice.domain.models import DocumentChunk, ChunkMetadata, TableRef, ImageRef

# ============================================================================
# EXAMPLE 1: OLD APPROACH (TABLES AS PLAIN TEXT)
# ============================================================================

print("\n" + "="*80)
print("BEFORE: Tables Treated as Plain Text (Current Implementation)")
print("="*80)

old_chunk1 = DocumentChunk(
    chunk_id="basic-text.pdf:p1:1",
    text="""Sample Document for PDF Testing
Introduction
This is a simple document created to test basic PDF functionality. It includes various text formatting
options to ensure proper rendering in PDF readers.
Text Formatting Examples
1. Bold text is used for emphasis.
2. Italic text can be used for titles or subtle emphasis.
3. Strikethrough is used to show deleted text.
Lists
Here's an example of an unordered list:
Item 1
Item 2
Item 3
And here's an ordered list:
1. First item
2. Second item
3. Third item
Quote
This is an example of a block quote. It can be used to highlight important information or
citations.
Table
Header 1 Header 2 Header 3
Row 1, Col 1 Row 1, Col 2 Row 1, Col 3
Row 2, Col 1 Row 2, Col 2 Row 2, Col 3""",
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1'}
    ),
    tables=()  # NO STRUCTURED TABLE DATA
)

old_chunk2 = DocumentChunk(
    chunk_id="basic-text.pdf:p1:2",
    text="""Table
Header 1 Header 2 Header 3
Row 1, Col 1 Row 1, Col 2 Row 1, Col 3
Row 2, Col 1 Row 2, Col 2 Row 2, Col 3
This document demonstrates various formatting options that should translate well to PDF format.
This sample PDF file is provided by Sample-Files.com. Visit us for more sample files and resources.""",
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1'}
    ),
    tables=()  # NO STRUCTURED TABLE DATA
)

print("\nOLD CHUNK #1 (First 200 chars):")
print(f"  Text: {old_chunk1.text[:200]}...")
print(f"  Tables: {old_chunk1.tables}")
print(f"  Problem: Table is SPLIT between chunks!")

print("\nOLD CHUNK #2 (First 200 chars):")
print(f"  Text: {old_chunk2.text[:200]}...")
print(f"  Tables: {old_chunk2.tables}")
print(f"  Problem: Duplicate table text (overlap), no structured data!")

# ============================================================================
# EXAMPLE 2: NEW APPROACH (TABLES AS STRUCTURED DATA)
# ============================================================================

print("\n" + "="*80)
print("AFTER: Tables Extracted as Structured Data")
print("="*80)

# The table from the document
sample_table = TableRef(
    table_id="basic-text.pdf:p1:table1",
    headers=["Header 1", "Header 2", "Header 3"],
    rows=[
        {"Header 1": "Row 1, Col 1", "Header 2": "Row 1, Col 2", "Header 3": "Row 1, Col 3"},
        {"Header 1": "Row 2, Col 1", "Header 2": "Row 2, Col 2", "Header 3": "Row 2, Col 3"},
    ]
)

# NEW CHUNK #1: Contains text BEFORE the table, no table splitting
new_chunk1 = DocumentChunk(
    chunk_id="basic-text.pdf:p1:1",
    text="""Sample Document for PDF Testing
Introduction
This is a simple document created to test basic PDF functionality. It includes various text formatting
options to ensure proper rendering in PDF readers.
Text Formatting Examples
1. Bold text is used for emphasis.
2. Italic text can be used for titles or subtle emphasis.
3. Strikethrough is used to show deleted text.
Lists
Here's an example of an unordered list:
Item 1
Item 2
Item 3
And here's an ordered list:
1. First item
2. Second item
3. Third item
Quote
This is an example of a block quote. It can be used to highlight important information or
citations.""",
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1'}
    ),
    tables=()  # No tables in this section
)

# NEW CHUNK #2: Contains the table as STRUCTURED DATA
new_chunk2 = DocumentChunk(
    chunk_id="basic-text.pdf:p1:table1",  # Unique ID for table
    text="",  # Empty text - table is in structured form
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1', 'chunk_type': 'table'}
    ),
    tables=(sample_table,)  # TABLE IS HERE AS STRUCTURED DATA!
)

# NEW CHUNK #3: Contains text AFTER the table
new_chunk3 = DocumentChunk(
    chunk_id="basic-text.pdf:p1:3",
    text="""This document demonstrates various formatting options that should translate well to PDF format.
This sample PDF file is provided by Sample-Files.com. Visit us for more sample files and resources.""",
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1'}
    ),
    tables=()  # No tables in this section
)

print("\nNEW CHUNK #1 (Text before table):")
print(f"  Chunk ID: {new_chunk1.chunk_id}")
print(f"  Tables: {new_chunk1.tables}")
print(f"  Benefit: Clean text chunk, no table data mixed in")

print("\nNEW CHUNK #2 (The table itself):")
print(f"  Chunk ID: {new_chunk2.chunk_id}")
print(f"  Tables: {new_chunk2.tables}")
print(f"  Benefit: Table is INTACT and STRUCTURED!")
print(f"  Table Headers: {new_chunk2.tables[0].headers if new_chunk2.tables else 'N/A'}")
print(f"  Table Rows: {new_chunk2.tables[0].rows if new_chunk2.tables else 'N/A'}")

print("\nNEW CHUNK #3 (Text after table):")
print(f"  Chunk ID: {new_chunk3.chunk_id}")
print(f"  Tables: {new_chunk3.tables}")
print(f"  Benefit: Clean text chunk, no overlap")

# ============================================================================
# KEY DIFFERENCES
# ============================================================================

print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)

print("""
OLD APPROACH:
  ❌ Table split across chunks 1 and 2
  ❌ Table data is plain text (hard to query)
  ❌ Overlap wastes storage
  ❌ Can't distinguish table from body text

NEW APPROACH:
  ✅ Table stays INTACT in its own chunk
  ✅ Table is STRUCTURED (dict of rows with named columns)
  ✅ No unnecessary overlap
  ✅ Can query structured data (e.g., "find rows where Header 1 = 'Row 1, Col 1'")
  ✅ Can embed table headers differently than text
  ✅ Easy to export tables to CSV/JSON

RETRIEVAL BENEFITS:
  
  Query: "What is in Header 2, Row 1?"
  
  OLD: Would need semantic search on messy text: 
       "Header 1 Header 2 Header 3 Row 1, Col 1 Row 1, Col 2..."
       
  NEW: Can query structured table directly:
       table.rows[0]["Header 2"]  # Returns: "Row 1, Col 2"
""")

print("\n" + "="*80)
print("PRACTICAL USAGE EXAMPLE")
print("="*80)

# Simulating a query result with the new approach
from rag_practice.domain.models import QueryResult

query_result = QueryResult(
    chunk_id="basic-text.pdf:p1:table1",
    text="",
    metadata=ChunkMetadata(
        source_id="basic-text.pdf",
        page=1,
        section=None,
        image_refs=[],
        extra={'source_id': 'basic-text.pdf', 'page': '1', 'chunk_type': 'table'}
    ),
    score=0.92,
    tables=(sample_table,)
)

print("\nQuery Result:")
print(f"  Chunk ID: {query_result.chunk_id}")
print(f"  Score: {query_result.score}")
print(f"  Has tables: {len(query_result.tables) > 0}")

if query_result.tables:
    table = query_result.tables[0]
    print(f"\n  Table Details:")
    print(f"    ID: {table.table_id}")
    print(f"    Headers: {table.headers}")
    print(f"    Rows:")
    for i, row in enumerate(table.rows, 1):
        print(f"      Row {i}: {dict(row)}")

print("\n" + "="*80)
