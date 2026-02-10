from __future__ import annotations

from typing import Sequence

from rag_practice.domain.models import DocumentChunk, TableRef


def table_to_text(table: TableRef, *, max_rows: int = 5) -> str:
    """Render a table to compact text for embedding/querying."""
    headers = " | ".join([str(h).strip() for h in table.headers if str(h).strip()])
    rows = []
    for row in table.rows[:max_rows]:
        row_vals = [str(row.get(h, "")).strip() for h in table.headers]
        rows.append(" | ".join(row_vals))
    body = "\n".join(r for r in rows if r.strip())
    parts = [p for p in [headers, body] if p]
    return "\n".join(parts).strip()


def chunk_to_embedding_text(chunk: DocumentChunk) -> str:
    """Create a non-empty text representation of a chunk for embedding."""
    meta_parts = [
        f"source_id: {chunk.metadata.source_id}",
        f"page: {chunk.metadata.page}",
        f"chunk_type: {chunk.metadata.extra.get('chunk_type', 'text')}",
    ]
    meta = " | ".join(meta_parts)

    text = (chunk.text or "").strip()
    if text:
        return f"{text}\n\n{meta}"
    if chunk.tables:
        rendered = "\n\n".join(
            table_to_text(t) for t in chunk.tables if table_to_text(t)
        ).strip()
        if rendered:
            return f"{rendered}\n\n{meta}"
    # Fallback to chunk_id to keep alignment with embeddings.
    return f"{chunk.chunk_id}\n\n{meta}"


def chunk_to_query_text(chunk: DocumentChunk, *, max_chars: int = 200) -> str:
    """Generate a representative query from chunk content (not metadata)."""
    text = (chunk.text or "").strip()
    if text:
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s[:max_chars]
        return text[:max_chars]

    if chunk.tables:
        rendered = "\n\n".join(
            table_to_text(t) for t in chunk.tables if table_to_text(t)
        ).strip()
        if rendered:
            for line in rendered.splitlines():
                s = line.strip()
                if s:
                    return s[:max_chars]
            return rendered[:max_chars]

    # Final fallback: include identifying metadata
    return f"{chunk.metadata.source_id} p{chunk.metadata.page} {chunk.metadata.extra.get('chunk_type', 'text')}"
