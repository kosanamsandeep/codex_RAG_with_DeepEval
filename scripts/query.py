from __future__ import annotations

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

from rag_practice.adapters.container import (
    build_ingest_pipeline,
    build_query_pipeline,
    load_env,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple RAG query over local PDFs.")
    parser.add_argument("question", help="User question to answer")
    parser.add_argument("--top-k", type=int, default=3, dest="top_k", help="Results to return")
    parser.add_argument("--source-id", dest="source_id", help="Optional source_id filter")
    parser.add_argument("--page", type=int, dest="page", help="Optional page filter")
    parser.add_argument(
        "--persist-dir",
        default="data/index",
        help="Directory to store/load FAISS index and metadata",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Skip loading/saving index (forces fresh ingest each run)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_env()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing; set it in .env")

    persist_dir = args.persist_dir
    index_path = f"{persist_dir}/faiss.index"
    meta_path = f"{persist_dir}/chunks.pkl"

    ingest = build_ingest_pipeline()
    if not args.no_persist:
        ingest.index.load(Path(index_path), Path(meta_path))  # type: ignore[attr-defined]

    if args.no_persist or not ingest.index._index or ingest.index._index.ntotal == 0:  # type: ignore[attr-defined]
        ingest.execute()
        if not args.no_persist:
            ingest.index.save(Path(index_path), Path(meta_path))  # type: ignore[attr-defined]

    query_use_case = build_query_pipeline(index=ingest.index)  # type: ignore[attr-defined]
    filters = {}
    if args.source_id:
        filters["source_id"] = args.source_id
    if args.page:
        filters["page"] = str(args.page)
    filters = filters or None
    results = query_use_case.execute(args.question, top_k=args.top_k, filters=filters)

    for idx, item in enumerate(results, start=1):
        print(f"\nResult {idx} (score {item.score:.4f})")
        print(f"Chunk ID: {item.chunk_id}")
        print(f"Source: {item.metadata.source_id} page {item.metadata.page}")
        print(f"Text: {item.text}")


if __name__ == "__main__":
    main()
