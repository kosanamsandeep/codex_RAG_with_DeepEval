"""
Test script to verify table detection and extraction in Phase 2
Run with: python test_table_extraction_phase2.py
"""

from pathlib import Path
from rag_practice.adapters.pdf_loader import PdfDocumentLoader
from rag_practice.adapters.chunking import MetadataAwareChunker


def main():
    print("="*80)
    print("PHASE 2: TABLE DETECTION AND EXTRACTION - TESTING")
    print("="*80)
    print()
    
    # Load PDFs
    print("1. Loading PDFs...")
    loader = PdfDocumentLoader(
        data_dir=Path("data"),
        image_output_dir=Path("data/processed/images")
    )
    documents = loader.load()
    print(f"✓ Loaded {len(documents)} documents")
    print()
    
    # Extract with table detection
    print("2. Extracting and chunking with table detection...")
    chunker = MetadataAwareChunker(chunk_size=800, chunk_overlap=120)
    chunks = chunker.chunk(documents)
    print(f"✓ Created {len(chunks)} chunks")
    print()
    
    # Analyze chunks
    print("3. CHUNK ANALYSIS:")
    print("-" * 80)
    
    text_chunks = [c for c in chunks if c.metadata.extra.get('chunk_type') == 'text']
    table_chunks = [c for c in chunks if c.metadata.extra.get('chunk_type') == 'table']
    
    print(f"Text chunks: {len(text_chunks)}")
    print(f"Table chunks: {len(table_chunks)}")
    print()
    
    # Show text chunks
    if text_chunks:
        print("TEXT CHUNKS:")
        print("-" * 80)
        for i, chunk in enumerate(text_chunks, 1):
            print(f"\n  Chunk {i}: {chunk.chunk_id}")
            print(f"  Page: {chunk.metadata.page}")
            print(f"  Text preview: {chunk.text[:100]}...")
            print()
    
    # Show table chunks
    if table_chunks:
        print("\nTABLE CHUNKS:")
        print("-" * 80)
        for i, chunk in enumerate(table_chunks, 1):
            print(f"\n  Chunk {i}: {chunk.chunk_id}")
            print(f"  Page: {chunk.metadata.page}")
            print(f"  Tables in chunk: {len(chunk.tables)}")
            
            for table_idx, table in enumerate(chunk.tables, 1):
                print(f"\n    Table {table_idx}: {table.table_id}")
                print(f"    Headers: {table.headers}")
                print(f"    Rows:")
                for row_idx, row in enumerate(table.rows, 1):
                    print(f"      Row {row_idx}: {dict(row)}")
            print()
    
    # Summary
    print("="*80)
    print("PHASE 2 TEST SUMMARY")
    print("="*80)
    print(f"✓ Documents loaded: {len(documents)}")
    print(f"✓ Total chunks created: {len(chunks)}")
    print(f"✓ Text chunks: {len(text_chunks)}")
    print(f"✓ Table chunks: {len(table_chunks)}")
    
    if table_chunks:
        total_tables = sum(len(c.tables) for c in table_chunks)
        print(f"✓ Total tables extracted: {total_tables}")
        print("\n✅ TABLE EXTRACTION WORKING!")
    else:
        print("\n⚠️ No tables detected (check if PDFs contain tables)")
    
    print()


if __name__ == "__main__":
    main()
