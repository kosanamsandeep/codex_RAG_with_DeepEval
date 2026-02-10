from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_practice.domain.models import ChunkMetadata, Document, DocumentChunk, ImageRef, TableRef


@dataclass(frozen=True, slots=True)
class MetadataAwareChunker:
    """
    Chunk documents into smaller pieces with metadata awareness.
    
    Handles three types of content:
    1. Text: Split using RecursiveCharacterTextSplitter
    2. Tables: Detected and extracted as structured TableRef objects
    3. Images: Tracked via references in chunk metadata
    
    Attributes:
        chunk_size (int): Target chunk size in characters (default: 800)
        chunk_overlap (int): Overlap between chunks in characters (default: 120)
    
    Example:
        ```python
        chunker = MetadataAwareChunker(chunk_size=800, chunk_overlap=120)
        documents = [Document(...), ...]
        chunks = chunker.chunk(documents)
        ```
    """
    chunk_size: int = 800
    chunk_overlap: int = 120

    def chunk(self, documents: Sequence[Document]) -> Sequence[DocumentChunk]:
        """
        Chunk all documents into smaller pieces.
        
        Process:
        1. For each page in each document:
           a. Detect and extract tables from page text
           b. Split remaining text into chunks
           c. Create text chunks with metadata
           d. Create table chunks with structured data
        2. Preserve image references in all chunks
        
        Args:
            documents: Sequence of Document objects to chunk
        
        Returns:
            Sequence of DocumentChunk objects
        
        Example:
            ```python
            documents = [pdf_doc_1, pdf_doc_2]
            chunks = chunker.chunk(documents)
            # chunks contains both text and table chunks with metadata
            ```
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        chunks: list[DocumentChunk] = []
        for doc in documents:
            chunks.extend(self._chunk_document(doc, splitter))
        return chunks

    def _chunk_document(
        self,
        document: Document,
        splitter: RecursiveCharacterTextSplitter,
    ) -> Iterable[DocumentChunk]:
        """
        Chunk a single document.
        
        Per-page process:
        1. Extract tables and text sections
        2. Chunk text sections recursively
        3. Create text chunks
        4. Create table chunks (text="" for tables)
        
        Args:
            document: Document to chunk
            splitter: RecursiveCharacterTextSplitter instance
        
        Yields:
            DocumentChunk objects (both text and table)
        """
        for page in document.pages:
            # Step 1: Detect and extract tables from page text
            text_sections, tables = self._extract_tables_from_text(page.text, document.source_id, page.page)
            
            # Step 2: Create chunks for text sections
            chunk_counter = 1
            for section_text in text_sections:
                if section_text.strip():  # Only create chunks for non-empty text
                    page_chunks = splitter.split_text(section_text)
                    for text in page_chunks:
                        chunk_id = f'{document.source_id}:p{page.page}:{chunk_counter}'
                        metadata = ChunkMetadata(
                            source_id=document.source_id,
                            page=page.page,
                            section=None,
                            image_refs=self._normalize_images(page.image_refs),
                            extra={
                                'source_id': document.source_id,
                                'page': str(page.page),
                                'chunk_type': 'text',
                            },
                        )
                        yield DocumentChunk(chunk_id=chunk_id, text=text, metadata=metadata)
                        chunk_counter += 1
            
            # Step 3: Create chunks for tables
            for table in tables:
                chunk_id = table.table_id
                metadata = ChunkMetadata(
                    source_id=document.source_id,
                    page=page.page,
                    section=None,
                    image_refs=self._normalize_images(page.image_refs),
                    extra={
                        'source_id': document.source_id,
                        'page': str(page.page),
                        'chunk_type': 'table',
                    },
                )
                yield DocumentChunk(chunk_id=chunk_id, text="", metadata=metadata, tables=(table,))

    def _normalize_images(self, images: Sequence[ImageRef]) -> Sequence[ImageRef]:
        """Normalize image references (currently identity function)."""
        return images
    
    def _extract_tables_from_text(
        self, text: str, source_id: str, page_num: int
    ) -> tuple[list[str], list[TableRef]]:
        """
        Extract structured tables from text while preserving text sections.
        
        Algorithm:
        1. Split text into lines
        2. Identify potential table lines (multi-word, space-separated)
        3. Group consecutive table lines
        4. Parse headers and rows
        5. Return remaining text + extracted tables
        
        Detection Heuristics (in _is_potential_table_line):
        - 2+ words per line
        - Each word < 100 characters
        - Line length > 10 characters
        
        Args:
            text: Page text to extract tables from
            source_id: Document identifier (for table IDs)
            page_num: Page number (for table IDs and metadata)
        
        Returns:
            Tuple of:
            - text_sections: List of text strings (tables removed)
            - tables: List of TableRef objects
        """
        tables: list[TableRef] = []
        lines = text.split('\n')
        
        text_sections = []
        current_text_section: list[str] = []
        table_counter = 1
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Detect table start: multiple consecutive columns separated by spaces/tabs
            if self._is_potential_table_line(line) and i + 1 < len(lines):
                # Look ahead to confirm it's a table
                next_line = lines[i + 1]
                if self._is_potential_table_line(next_line):
                    # Found a table! Save current text section
                    if current_text_section:
                        text_sections.append('\n'.join(current_text_section).strip())
                        current_text_section = []
                    
                    # Extract the full table
                    table_lines, table_end = self._extract_table_lines(lines, i)
                    table = self._parse_table(table_lines, source_id, page_num, table_counter)
                    if table:
                        tables.append(table)
                        table_counter += 1
                    i = table_end
                    continue
            
            current_text_section.append(line)
            i += 1
        
        # Add remaining text
        if current_text_section:
            text_sections.append('\n'.join(current_text_section).strip())
        
        return text_sections, tables

    def _is_potential_table_line(self, line: str) -> bool:
        """
        Heuristic to identify if a line looks like table content.
        
        Criteria:
        - Non-empty after stripping
        - 2+ words
        - All words < 100 characters (filters prose paragraphs)
        - Line length > 10 characters
        
        Args:
            line: Text line to check
        
        Returns:
            True if line could be a table row, False otherwise
        """
        if not line.strip():
            return False
        
        # A table line has multiple words separated by at least one space
        words = line.strip().split()
        
        # Minimum criteria: 2+ words, each word is relatively short (< 100 chars)
        # and none of the words are extremely short (0 chars) when split
        return (
            len(words) >= 2 
            and all(len(w) > 0 for w in words)
            and all(len(w) < 100 for w in words)
            and len(line.strip()) > 10  # Line must have some content
        )

    def _extract_table_lines(
        self, lines: list[str], start_idx: int
    ) -> tuple[list[str], int]:
        """
        Extract consecutive table lines starting from start_idx.
        
        Collects contiguous lines that match the table line pattern.
        Stops on empty lines or non-table content.
        
        Args:
            lines: Full list of text lines
            start_idx: Starting index for table extraction
        
        Returns:
            Tuple of:
            - table_lines: List of consecutive table lines
            - next_idx: Index to resume searching (after last table line)
        """
        table_lines = [lines[start_idx]]
        i = start_idx + 1
        
        # Continue collecting table lines while they look like table content
        while i < len(lines):
            line = lines[i]
            if not line.strip():  # Empty line might separate tables
                i += 1
                break
            if self._is_potential_table_line(line):
                table_lines.append(line)
                i += 1
            else:
                break
        
        return table_lines, i

    def _parse_table(
        self, table_lines: list[str], source_id: str, page_num: int, table_idx: int
    ) -> TableRef | None:
        """
        Parse table lines into a TableRef object.
        
        Process:
        1. Extract headers from first line
        2. Parse remaining lines as data rows
        3. Match cells to headers by position
        4. Return structured TableRef
        
        Args:
            table_lines: List of table row strings
            source_id: Document identifier
            page_num: Page number
            table_idx: Table counter on page
        
        Returns:
            TableRef object or None if parsing fails
        """
        if len(table_lines) < 2:
            return None
        
        # Parse headers - handle both single and multi-word headers
        header_line = table_lines[0].strip()
        headers = self._smart_split_table_line(header_line)
        
        if not headers or len(headers) < 2:
            return None
        
        # Remaining lines are data rows
        rows: list[Mapping[str, str]] = []
        for line in table_lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            cells = self._smart_split_table_line(line)
            
            # Match cells to headers - use positional matching
            if cells:
                # Pad cells to match header count
                while len(cells) < len(headers):
                    cells.append("")
                cells = cells[:len(headers)]  # Truncate if too many
                
                row = {headers[i]: cells[i] for i in range(len(headers))}
                rows.append(row)
        
        if not rows:
            return None
        
        table_id = f"{source_id}:p{page_num}:table{table_idx}"
        return TableRef(table_id=table_id, headers=headers, rows=rows)

    def _smart_split_table_line(self, line: str) -> list[str]:
        """
        Smart split for table lines.
        
        Strategy:
        1. First try to split by multiple spaces (2+)
           - Common in PDF tables with aligned columns
        2. Fall back to single space split
           - For compact or CSV-style tables
        
        Args:
            line: Table line to parse into columns
        
        Returns:
            List of cell values (stripped)
        """
        line = line.strip()
        
        # Try multiple spaces first (common in PDF tables)
        if '  ' in line:
            parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
            if len(parts) >= 2:
                return parts
        
        # Fall back to single space split
        parts = [p.strip() for p in line.split() if p.strip()]
        return parts