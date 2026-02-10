from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_practice.domain.models import ChunkMetadata, Document, DocumentChunk, ImageRef, TableRef


@dataclass(frozen=True, slots=True)
class MetadataAwareChunker:
    chunk_size: int = 800
    chunk_overlap: int = 120

    def chunk(self, documents: Sequence[Document]) -> Sequence[DocumentChunk]:
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
        return images
    def _extract_tables_from_text(
        self, text: str, source_id: str, page_num: int
    ) -> tuple[list[str], list[TableRef]]:
        """
        Extract tables from text while preserving non-table content.
        
        Returns:
            Tuple of (text_sections, tables) where:
            - text_sections: List of text portions with tables removed
            - tables: List of extracted TableRef objects
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
        """Check if a line looks like it could be part of a table."""
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
        """Extract consecutive table lines starting from start_idx."""
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
        """Parse table lines into a TableRef object."""
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
        First try to split by multiple spaces (standard table format).
        If that doesn't work well, fall back to splitting by single space.
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