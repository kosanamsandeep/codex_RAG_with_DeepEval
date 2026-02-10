from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from langchain_openai import OpenAIEmbeddings


@dataclass(frozen=True, slots=True)
class OpenAITextEmbedder:
    model: str = 'text-embedding-3-small'

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        embeddings = OpenAIEmbeddings(model=self.model)
        return embeddings.embed_documents(list(texts))

    def embed_query(self, text: str) -> Sequence[float]:
        embeddings = OpenAIEmbeddings(model=self.model)
        return embeddings.embed_query(text)
