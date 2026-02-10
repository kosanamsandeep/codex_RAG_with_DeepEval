from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_practice.domain.models import ChunkMetadata, Document, DocumentChunk, ImageRef


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
            page_chunks = splitter.split_text(page.text)
            for idx, text in enumerate(page_chunks, start=1):
                chunk_id = f'{document.source_id}:p{page.page}:{idx}'
                metadata = ChunkMetadata(
                    source_id=document.source_id,
                    page=page.page,
                    section=None,
                    image_refs=self._normalize_images(page.image_refs),
                    extra={
                        'source_id': document.source_id,
                        'page': str(page.page),
                    },
                )
                yield DocumentChunk(chunk_id=chunk_id, text=text, metadata=metadata)

    def _normalize_images(self, images: Sequence[ImageRef]) -> Sequence[ImageRef]:
        return images
