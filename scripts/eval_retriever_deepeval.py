from __future__ import annotations

import os
from pathlib import Path
import json
import sys

from dotenv import load_dotenv
import argparse

# Project imports
from rag_practice.adapters.container import build_query_pipeline, build_ingest_pipeline, load_env
from rag_practice.domain.models import ChunkMetadata

# Note: `deepeval` is an external evaluation framework. This script assumes
# a minimal API: a ranking evaluator that can compute precision@k and recall@k
# from a list of predicted doc ids and a set of ground-truth doc ids.
# If `deepeval` isn't installed, the script will fall back to a simple local
# evaluator implementation.


class SimpleEvaluator:
    def precision_at_k(self, predicted: list[str], ground_truth: set[str], k: int) -> float:
        if k <= 0:
            return 0.0
        pred_topk = predicted[:k]
        if not pred_topk:
            return 0.0
        tp = sum(1 for p in pred_topk if p in ground_truth)
        return tp / len(pred_topk)

    def recall_at_k(self, predicted: list[str], ground_truth: set[str], k: int) -> float:
        if not ground_truth:
            return 0.0
        pred_topk = predicted[:k]
        tp = sum(1 for p in pred_topk if p in ground_truth)
        return tp / len(ground_truth)


def load_chunks_output(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        # support either JSON-lines or full JSON list
        text = fh.read().strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            # if data is a dict with a `queries` key, normalize
            if isinstance(data, dict) and "queries" in data:
                return data["queries"]
            if isinstance(data, list):
                return data
        except Exception:
            # try to parse as JSON lines
            items = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    # skip malformed lines
                    continue
            if items:
                return items
    # fallback: if file is a human-readable chunks report, parse chunk ids and text
    text = path.read_text(encoding="utf-8")
    if "CHUNK #" in text and "Chunk ID:" in text:
        return parse_plain_chunks_report(text)
    return []


def parse_plain_chunks_report(text: str) -> list[dict]:
    items: list[dict] = []
    lines = text.splitlines()
    cur = None
    capture = False
    for line in lines:
        if line.strip().startswith("CHUNK #"):
            # start a new chunk
            if cur:
                items.append(cur)
            cur = {"chunk_id": None, "text": "", "question": None}
            capture = False
            continue
        if line.strip().startswith("Chunk ID:") and cur is not None:
            cid = line.split("Chunk ID:", 1)[1].strip()
            cur["chunk_id"] = cid
            continue
        if line.strip().startswith("Text Content:") and cur is not None:
            capture = True
            continue
        if capture and cur is not None:
            # stop capture on separator lines
            if line.strip().startswith("-" * 10) or line.strip().startswith("==="):
                capture = False
                continue
            cur["text"] += line + "\n"
    if cur:
        # finalize
        # create a simple question from the first non-empty line of text
        first_line = "".join([l for l in cur["text"].splitlines() if l.strip()])
        first_line = first_line.splitlines()[0] if first_line else ""
        cur["question"] = first_line or cur.get("chunk_id")
        items.append(cur)
    # normalize to expected format: list of dicts with 'query' and 'ground_truth'
    out: list[dict] = []
    for it in items:
        q = it.get("question") or (it.get("text") or "").splitlines()[0:1]
        if isinstance(q, list):
            q = q[0] if q else ""
        out.append({"query": q, "ground_truth": [it.get("chunk_id")]})
    return out


def extract_ground_truth(item: dict) -> set[str]:
    # Expect each item to contain a ground-truth list under 'ground_truth' or 'relevant_chunk_ids'
    if "ground_truth" in item and isinstance(item["ground_truth"], list):
        return set(item["ground_truth"])
    if "relevant_chunk_ids" in item and isinstance(item["relevant_chunk_ids"], list):
        return set(item["relevant_chunk_ids"])
    # fallback: if item contains 'chunks' with metadata and 'is_relevant'
    gt = set()
    for c in item.get("chunks", []):
        if c.get("is_relevant"):
            cid = c.get("chunk_id") or c.get("id")
            if cid:
                gt.add(cid)
    return gt


def build_predictions(results) -> list[str]:
    # results is expected to be a sequence of QueryResult-like objects
    preds: list[str] = []
    for r in results:
        cid = None

        # 1) direct attributes on result objects
        if hasattr(r, "chunk_id"):
            cid = getattr(r, "chunk_id")
        elif hasattr(r, "id"):
            cid = getattr(r, "id")

        # 2) mapping-style results
        if cid is None and isinstance(r, dict):
            cid = r.get("chunk_id") or r.get("id")

        # 3) look inside metadata (dataclass or dict)
        if cid is None:
            meta = getattr(r, "metadata", None)
            if meta is None and isinstance(r, dict):
                meta = r.get("metadata")
            if meta is not None:
                # dataclass / object with attributes
                if hasattr(meta, "chunk_id"):
                    cid = getattr(meta, "chunk_id")
                elif hasattr(meta, "id"):
                    cid = getattr(meta, "id")
                # mapping-like metadata
                elif isinstance(meta, dict):
                    cid = meta.get("chunk_id") or meta.get("id")

        # fallback: hash of text
        if cid is None:
            text = getattr(r, "text", None) or (r.get("text") if isinstance(r, dict) else None) or ""
            cid = str(hash(text))

        preds.append(str(cid))

    return preds


def main():
    parser = argparse.ArgumentParser(description="Evaluate retriever using deepeval or a simple fallback.")
    parser.add_argument("--persist-dir", default="data/index", help="Directory to load/save FAISS index and metadata")
    parser.add_argument("--no-persist", action="store_true", help="Skip loading/saving index (forces fresh ingest)")
    parser.add_argument("--queries", help="Path to queries JSONL file (query_id, query)")
    parser.add_argument("--qrels", help="Path to qrels JSONL file (query_id, relevant_ids)")
    parser.add_argument("--rerank", action="store_true", help="Enable lightweight reranker")
    parser.add_argument("--rerank-weight", type=float, default=0.35, dest="rerank_weight", help="Rerank weight (0-1)")
    parser.add_argument("--rerank-multiplier", type=int, default=3, dest="rerank_multiplier", help="Pre-retrieval multiplier")
    parser.add_argument("--diagnose", type=int, default=0, help="Print worst N queries by top-1 hit")
    args = parser.parse_args()

    load_env()
    load_dotenv()

    items = None
    # if both queries and qrels are provided, load them as the eval set
    if args.queries and args.qrels:
        qpath = Path(args.queries)
        rpath = Path(args.qrels)
        if not qpath.exists() or not rpath.exists():
            print("--queries or --qrels path not found")
            sys.exit(1)
        # load queries into items where each item is {"query_id","query","ground_truth": [...]}
        items = []
        with qpath.open("r", encoding="utf-8") as qf:
            qlines = [json.loads(l) for l in qf if l.strip()]
        with rpath.open("r", encoding="utf-8") as rf:
            rlines = {json.loads(l)["query_id"]: json.loads(l).get("relevant_ids", []) for l in rf if l.strip()}
        for q in qlines:
            qid = q.get("query_id") or q.get("id")
            items.append({"query": q.get("query") or q.get("text"), "ground_truth": rlines.get(qid, []), "query_id": qid})

    # fallback to legacy chunks_output.txt parsing
    if items is None:
        chunks_path = Path("chunks_output.txt")
        if not chunks_path.exists():
            print("chunks_output.txt not found and no --queries/--qrels provided.")
            sys.exit(1)

        items = load_chunks_output(chunks_path)
        if not items:
            print("No queries/ground-truth found in chunks_output.txt")
            sys.exit(1)

    # build ingest/query pipeline and ensure index is loaded
    ingest = build_ingest_pipeline()
    persist_dir = Path(args.persist_dir)
    index_path = persist_dir / "faiss.index"
    meta_path = persist_dir / "chunks.pkl"

    if not args.no_persist:
        try:
            ingest.index.load(index_path, meta_path)  # type: ignore[attr-defined]
        except Exception:
            pass

    if args.no_persist or not getattr(ingest.index, "_index", None) or getattr(ingest.index, "_index", None).ntotal == 0:  # type: ignore[attr-defined]
        ingest.execute()
        if not args.no_persist:
            try:
                ingest.index.save(index_path, meta_path)  # type: ignore[attr-defined]
            except Exception:
                pass

    query_uc = build_query_pipeline(
        index=ingest.index,  # type: ignore[arg-type]
        enable_rerank=args.rerank,
        rerank_multiplier=args.rerank_multiplier,
        rerank_weight=args.rerank_weight,
    )

    # try to import deepeval evaluator
    try:
        from deepeval import RankEvaluator
        evaluator = RankEvaluator()
        has_deepeval = True
    except Exception:
        evaluator = SimpleEvaluator()
        has_deepeval = False

    ks = [1, 3, 5]
    agg = {k: {"precision": [], "recall": []} for k in ks}

    misses: list[dict] = []
    for itm in items:
        # Skip if item is not a dictionary (e.g., int from malformed JSON)
        if not isinstance(itm, dict):
            print(f"Skipping non-dict item: {itm} (type: {type(itm).__name__})")
            continue
        question = itm.get("question") or itm.get("query")
        if not question:
            continue
        ground_truth = extract_ground_truth(itm)
        results = query_uc.execute(question, top_k=max(ks))
        preds = build_predictions(results)
        for k in ks:
            p = evaluator.precision_at_k(preds, ground_truth, k) if not has_deepeval else evaluator.precision_at_k(preds, list(ground_truth), k)
            r = evaluator.recall_at_k(preds, ground_truth, k) if not has_deepeval else evaluator.recall_at_k(preds, list(ground_truth), k)
            agg[k]["precision"].append(p)
            agg[k]["recall"].append(r)

        if args.diagnose > 0:
            top1 = preds[0] if preds else None
            hit = 1 if top1 in ground_truth else 0
            misses.append(
                {
                    "hit": hit,
                    "query": question,
                    "query_id": itm.get("query_id"),
                    "top1": top1,
                    "ground_truth": list(ground_truth),
                }
            )

    # compute averages
    summary = {}
    for k in ks:
        ps = agg[k]["precision"]
        rs = agg[k]["recall"]
        summary[f"p@{k}"] = sum(ps) / len(ps) if ps else 0.0
        summary[f"r@{k}"] = sum(rs) / len(rs) if rs else 0.0

    print("Evaluation summary:")
    print(json.dumps(summary, indent=2))

    if args.diagnose > 0 and misses:
        misses.sort(key=lambda x: x["hit"])
        print("\nWorst queries (top-1 misses):")
        for row in misses[: args.diagnose]:
            print(f"- query_id={row['query_id']} top1={row['top1']} gt={row['ground_truth']}")
            print(f"  query={row['query']}")


if __name__ == "__main__":
    main()
