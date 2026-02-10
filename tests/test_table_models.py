"""
Quick test to validate TableRef model and DocumentChunk integration
Run with: pytest tests/test_table_models.py -v
"""

import pytest
from rag_practice.domain.models import TableRef, DocumentChunk, ChunkMetadata, QueryResult


class TestTableRefModel:
    """Test TableRef dataclass"""

    def test_table_ref_creation(self):
        """Test creating a TableRef object"""
        table = TableRef(
            table_id="test.pdf:p1:table1",
            headers=["Name", "Age", "City"],
            rows=[
                {"Name": "Alice", "Age": "30", "City": "NYC"},
                {"Name": "Bob", "Age": "25", "City": "LA"},
            ]
        )
        assert table.table_id == "test.pdf:p1:table1"
        assert len(table.headers) == 3
        assert len(table.rows) == 2
        assert table.rows[0]["Name"] == "Alice"

    def test_table_ref_immutability(self):
        """Test that TableRef is frozen (immutable)"""
        table = TableRef(
            table_id="test.pdf:p1:table1",
            headers=["A", "B"],
            rows=[{"A": "1", "B": "2"}]
        )
        with pytest.raises(AttributeError):
            table.headers = ["C", "D"]

    def test_table_ref_with_empty_rows(self):
        """Test TableRef with no rows (headers only)"""
        table = TableRef(
            table_id="test.pdf:p1:table1",
            headers=["Col1", "Col2"],
            rows=[]
        )
        assert len(table.rows) == 0
        assert len(table.headers) == 2


class TestDocumentChunkWithTables:
    """Test DocumentChunk with table support"""

    def test_chunk_without_tables(self):
        """Test creating a chunk without tables"""
        chunk = DocumentChunk(
            chunk_id="doc1:p1:1",
            text="Some text here",
            metadata=ChunkMetadata(
                source_id="doc1",
                page=1,
                section=None,
                image_refs=[],
                extra={}
            ),
            tables=()  # Default: no tables
        )
        assert chunk.tables == ()
        assert len(chunk.tables) == 0

    def test_chunk_with_single_table(self):
        """Test creating a chunk with one table"""
        table = TableRef(
            table_id="doc1:p1:table1",
            headers=["H1", "H2"],
            rows=[{"H1": "V1", "H2": "V2"}]
        )
        chunk = DocumentChunk(
            chunk_id="doc1:p1:table1",
            text="",  # Can have empty text for table-only chunks
            metadata=ChunkMetadata(
                source_id="doc1",
                page=1,
                section=None,
                image_refs=[],
                extra={"chunk_type": "table"}
            ),
            tables=(table,)
        )
        assert len(chunk.tables) == 1
        assert chunk.tables[0].table_id == "doc1:p1:table1"

    def test_chunk_with_multiple_tables(self):
        """Test creating a chunk with multiple tables"""
        table1 = TableRef(
            table_id="doc1:p1:table1",
            headers=["A", "B"],
            rows=[{"A": "1", "B": "2"}]
        )
        table2 = TableRef(
            table_id="doc1:p1:table2",
            headers=["X", "Y"],
            rows=[{"X": "10", "Y": "20"}]
        )
        chunk = DocumentChunk(
            chunk_id="doc1:p1:tables",
            text="Text with multiple tables",
            metadata=ChunkMetadata(
                source_id="doc1",
                page=1,
                section=None,
                image_refs=[],
                extra={}
            ),
            tables=(table1, table2)
        )
        assert len(chunk.tables) == 2
        assert chunk.tables[0].table_id == "doc1:p1:table1"
        assert chunk.tables[1].table_id == "doc1:p1:table2"

    def test_chunk_immutability(self):
        """Test that DocumentChunk is frozen"""
        chunk = DocumentChunk(
            chunk_id="doc1:p1:1",
            text="text",
            metadata=ChunkMetadata(
                source_id="doc1",
                page=1,
                section=None,
                image_refs=[],
                extra={}
            ),
            tables=()
        )
        with pytest.raises(AttributeError):
            chunk.text = "new text"


class TestQueryResultWithTables:
    """Test QueryResult with table support"""

    def test_query_result_with_table(self):
        """Test QueryResult containing a table"""
        table = TableRef(
            table_id="doc1:p1:table1",
            headers=["Name", "Score"],
            rows=[
                {"Name": "Test1", "Score": "95"},
                {"Name": "Test2", "Score": "87"},
            ]
        )
        result = QueryResult(
            chunk_id="doc1:p1:table1",
            text="",
            metadata=ChunkMetadata(
                source_id="doc1",
                page=1,
                section=None,
                image_refs=[],
                extra={"chunk_type": "table"}
            ),
            score=0.92,
            tables=(table,)
        )
        assert result.score == 0.92
        assert len(result.tables) == 1
        assert result.tables[0].rows[0]["Name"] == "Test1"


class TestTableComparison:
    """Demonstrate old vs new approach"""

    def test_old_approach_text_split(self):
        """Old approach: table stored as plain text, gets split"""
        # BEFORE: Table would be duplicated in overlap
        chunk1_text = "Text before...\nTable\nHeader1 Header2\nRow1Val1 Row1Val2"
        chunk2_text = "Table\nHeader1 Header2\nRow1Val1 Row1Val2\nText after..."
        
        chunk1 = DocumentChunk(
            chunk_id="doc:p1:1",
            text=chunk1_text,
            metadata=ChunkMetadata("doc", 1, None, [], {}),
            tables=()  # NO STRUCTURE
        )
        chunk2 = DocumentChunk(
            chunk_id="doc:p1:2",
            text=chunk2_text,
            metadata=ChunkMetadata("doc", 1, None, [], {}),
            tables=()  # NO STRUCTURE
        )
        
        # Table is mixed with text and repeated
        assert "Table" in chunk1.text
        assert "Table" in chunk2.text
        assert len(chunk1.tables) == 0
        assert len(chunk2.tables) == 0

    def test_new_approach_table_extracted(self):
        """New approach: table extracted as structured data"""
        table = TableRef(
            table_id="doc:p1:table1",
            headers=["Header1", "Header2"],
            rows=[{"Header1": "Row1Val1", "Header2": "Row1Val2"}]
        )
        
        # THREE separate chunks:
        chunk1 = DocumentChunk(
            chunk_id="doc:p1:1",
            text="Text before...",
            metadata=ChunkMetadata("doc", 1, None, [], {}),
            tables=()  # Only text
        )
        chunk2 = DocumentChunk(
            chunk_id="doc:p1:table1",
            text="",  # Empty (table is structured)
            metadata=ChunkMetadata("doc", 1, None, [], {"type": "table"}),
            tables=(table,)  # TABLE IS STRUCTURED
        )
        chunk3 = DocumentChunk(
            chunk_id="doc:p1:2",
            text="Text after...",
            metadata=ChunkMetadata("doc", 1, None, [], {}),
            tables=()  # Only text
        )
        
        # Benefits:
        assert chunk1.text == "Text before..."
        assert len(chunk1.tables) == 0
        
        assert chunk2.text == ""  # Pure structure, no text
        assert len(chunk2.tables) == 1
        assert chunk2.tables[0].rows[0]["Header1"] == "Row1Val1"  # Direct query!
        
        assert chunk3.text == "Text after..."
        assert len(chunk3.tables) == 0
        
        # No overlap, clear separation of concerns
        total_table_text = sum(len(c.text) for c in [chunk1, chunk2, chunk3])
        old_total = len("Text before...\nTable\nHeader1 Header2\nRow1Val1 Row1Val2\nText after...")
        # New approach is more efficient (no duplication)
        assert total_table_text <= old_total


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
