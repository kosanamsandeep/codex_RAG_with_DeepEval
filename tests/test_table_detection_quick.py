"""
Quick test of table detection logic
"""

from rag_practice.adapters.chunking import MetadataAwareChunker

# Sample text with a table
sample_text = """Introduction
This is some text before the table.

Table
Header 1 Header 2 Header 3
Row 1, Col 1 Row 1, Col 2 Row 1, Col 3
Row 2, Col 1 Row 2, Col 2 Row 2, Col 3

This is text after the table."""

chunker = MetadataAwareChunker()

print("Testing table detection...")
print("="*80)
print(f"Sample text:\n{sample_text}")
print("="*80)

# Test table extraction
text_sections, tables = chunker._extract_tables_from_text(sample_text, "test.pdf", 1)

print(f"\nResults:")
print(f"Text sections found: {len(text_sections)}")
for i, section in enumerate(text_sections, 1):
    print(f"\n  Section {i}:")
    print(f"    {repr(section[:50])}")

print(f"\nTables found: {len(tables)}")
for table in tables:
    print(f"\n  Table: {table.table_id}")
    print(f"  Headers: {table.headers}")
    for i, row in enumerate(table.rows, 1):
        print(f"  Row {i}: {dict(row)}")
