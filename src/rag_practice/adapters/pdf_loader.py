from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image
from pypdf import PdfReader

from rag_practice.domain.models import Document, ImageRef, PageContent


@dataclass(frozen=True, slots=True)
class PdfDocumentLoader:
    data_dir: Path
    image_output_dir: Path

    def load(self) -> Sequence[Document]:
        pdf_paths = sorted(self.data_dir.glob('*.pdf'))
        documents: list[Document] = []
        for path in pdf_paths:
            documents.append(self._load_single(path))
        return documents

    def _load_single(self, path: Path) -> Document:
        reader = PdfReader(str(path))
        pages: list[PageContent] = []
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ''
            image_refs = list(self._extract_images(page, path.stem, page_index))
            pages.append(PageContent(page=page_index, text=text, image_refs=image_refs))
        return Document(source_id=path.name, pages=pages)

    def _extract_images(self, page, source_id: str, page_index: int) -> Iterable[ImageRef]:
        self.image_output_dir.mkdir(parents=True, exist_ok=True)

        if not hasattr(page, 'images'):
            return []

        image_refs: list[ImageRef] = []
        try:
            images = list(page.images)
        except Exception:
            return []

        for idx, image in enumerate(images, start=1):
            try:
                data = image.data
            except Exception:
                continue

            ext = self._detect_extension(data) or 'png'
            filename = f'{source_id}_p{page_index}_{idx}.{ext}'
            output_path = self.image_output_dir / filename
            try:
                output_path.write_bytes(data)
            except Exception:
                continue
            image_refs.append(ImageRef(path=str(output_path), page=page_index, caption=None))
        return image_refs

    def _detect_extension(self, data: bytes) -> str | None:
        try:
            with Image.open(BytesIO(data)) as img:
                fmt = img.format
                if fmt:
                    return fmt.lower()
        except Exception:
            return None
        return None
