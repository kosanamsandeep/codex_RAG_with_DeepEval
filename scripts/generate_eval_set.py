from __future__ import annotations

import argparse
import json
from pathlib import Path
import pickle
from typing import Iterable

from rag_practice.domain.models import DocumentChunk
from rag_practice.domain.text_utils import chunk_to_query_text


def load_chunks(metadata_path: Path) -> list[DocumentChunk]:
    with metadata_path.open("rb") as fh:
        return pickle.load(fh)


def make_query_from_chunk(chunk: DocumentChunk, max_chars: int = 200) -> str:
    return chunk_to_query_text(chunk, max_chars=max_chars)


def write_jsonl(items: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")


def generate(metadata_path: Path, out_dir: Path, sample_rate: float = 1.0, min_len: int = 10):
    chunks = load_chunks(metadata_path)
    queries = []
    qrels = []
    for c in chunks:
        if sample_rate < 1.0:
            import random

            if random.random() > sample_rate:
                continue
        qtext = make_query_from_chunk(c)
        if len(qtext) < min_len:
            continue
        queries.append({"query_id": c.chunk_id, "query": qtext})
        qrels.append({"query_id": c.chunk_id, "relevant_ids": [c.chunk_id]})

    write_jsonl(queries, out_dir / "eval_queries.jsonl")
    write_jsonl(qrels, out_dir / "eval_qrels.jsonl")
    print(f"Wrote {len(queries)} queries to {out_dir}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--metadata", default="data/index/chunks.pkl", help="Pickle file with chunks list")
    p.add_argument("--out-dir", default="data/index/eval", help="Output directory for queries/qrels")
    p.add_argument("--sample-rate", type=float, default=1.0, help="Fraction of chunks to sample")
    p.add_argument("--min-len", type=int, default=10, dest="min_len", help="Minimum query length")
    args = p.parse_args()
    generate(Path(args.metadata), Path(args.out_dir), sample_rate=args.sample_rate, min_len=args.min_len)


if __name__ == "__main__":
    main()
