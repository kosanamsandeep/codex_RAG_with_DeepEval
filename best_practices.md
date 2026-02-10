# RAG Pipeline Best Practices (This Project)

This document summarizes the top-level steps in the pipeline we built and why each step adds measurable value.

---

## 1. Ingest PDFs (Layout-Aware Extraction)
**What**: Extract text, tables, and images from PDFs using `pdfplumber` (layout-aware) with a `pypdf` fallback.  
**Why it adds value**:
- Preserves reading order in complex layouts (bank statements, multi-column docs).
- Improves table recovery by capturing row/column structure.
- Reduces retrieval errors caused by scrambled text.

---

## 2. Chunking (Text + Table Separation)
**What**: Split text into fixed-size chunks and extract tables into structured `TableRef` objects.  
**Why it adds value**:
- Keeps tables **atomic** (not split across chunks).
- Makes table rows queryable by column name.
- Prevents duplicated table text due to chunk overlap.
- Improves precision for structured queries (e.g., transactions by date).

---

## 3. Metadata-Aware Embeddings
**What**: Embed chunks with appended metadata (`source_id`, `page`, `chunk_type`).  
**Why it adds value**:
- Disambiguates near-duplicate content across pages.
- Improves retrieval precision for repeated headers/boilerplate.
- Enables stronger filtering and context control downstream.

---

## 4. Vector Indexing (FAISS)
**What**: Store embeddings in FAISS and retrieve top-k by similarity.  
**Why it adds value**:
- Fast semantic retrieval at scale.
- Supports metadata-based filtering at query time.
- Enables persistent indexing for faster iteration.

---

## 5. Optional Reranking (Lexical Signal)
**What**: Reorder retrieved candidates using a lightweight token-overlap score.  
**Why it adds value**:
- Improves top-1 accuracy (p@1) without heavy dependencies.
- Helps when the query includes exact phrases (“Base Branch”, dates, IDs).
- Provides a safer fallback if embeddings over-generalize.

---

## 6. Metadata Filtering
**What**: Filter results by `source_id`, `page`, and `chunk_type`.  
**Why it adds value**:
- Narrow search to a specific document or page range.
- Prevents unrelated documents from polluting answers.
- Essential for compliance workflows and traceability.

---

## 7. Table-Aware Answering (Deterministic Extraction)
**What**: For date-based queries, extract rows directly from `TableRef` instead of relying on LLM inference.  
**Why it adds value**:
- Guarantees complete row listing (no hallucination).
- Works even when LLM answers are vague or incomplete.
- Best for numeric/financial domains (bank statements).

---

## 8. Evaluation with DeepEval (Precision/Recall)
**What**: Measure `p@k` and `r@k` using query/qrel sets from indexed chunks.  
**Why it adds value**:
- Quantifies retrieval quality before prompt changes.
- Prevents regressions when adjusting chunking or embeddings.
- Provides objective improvements (e.g., reranking lifts p@1).

---

## 9. UI for Debug & Trust
**What**: Streamlit UI with citations, raw chunk preview, and filtering.  
**Why it adds value**:
- Makes retrieval transparent and debuggable.
- Allows manual validation of sources.
- Builds user trust in answers.

---

## Summary of Value Gains
- **PDF Layout Issues**: Fixed via `pdfplumber` extraction + table rendering.
- **Table Search Efficiency**: Structured `TableRef` + deterministic row extraction.
- **Retrieval Accuracy**: Metadata-aware embeddings + reranking.
- **Reliability & Governance**: Metadata filters + citations.
- **Quality Control**: DeepEval metrics for measurable improvements.

