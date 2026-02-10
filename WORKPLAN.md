# RAG Practice Workplan (LangChain + Vector DB)

## Goal
Build a small Retrieval Augmented Generation (RAG) app with:
- LangChain
- A simple vector database (FAISS)
- OpenAI multimodal support
- Metadata-aware chunking and retrieval
- Evaluation with DeepEval
- Clean architecture inspired by *Cosmic Python* (domain, application, adapters)
- Test-driven development, SOLID, type annotations

## Workflow

### 1) Project setup
- [x] Initialize repo structure (`src/`, `tests/`, `data/`, `scripts/`)
- [x] Add `pyproject.toml` with dependencies and tooling (pytest, mypy, ruff)
- [x] Create `.env` and `.gitignore` (ensure `.env` is ignored)
- [x] Add a minimal `README.md` with run instructions

### 2) Architecture scaffolding (Cosmic Python style)
- [x] Define domain layer (entities, value objects, interfaces)
- [x] Define application layer (use cases/services, ports)
- [x] Define adapters (LangChain loaders, vector DB, OpenAI client)
- [ ] Wire dependencies via a composition root

### 3) Data sources (small PDFs with images)
- [x] Collect 2-3 small public-domain PDFs with embedded images
- [ ] Store under `data/raw/` and document provenance
- [ ] Add a script to verify file size and page count

### 4) Ingestion + chunking
- [x] Implement PDF loader with image extraction
- [x] Design chunking strategy (text + image captions)
- [x] Add metadata schema (source, page, section, image refs)
- [ ] Unit tests for chunking and metadata consistency

### 5) Vector database
- [x] Choose a simple vector DB (FAISS)
- [x] Implement adapter for index creation and persistence
- [x] Add tests for insert, query, metadata filters, and persistence

### 6) Multimodal pipeline
- [ ] Implement OpenAI multimodal embedding (text + image)
- [ ] Integrate with LangChain retriever
- [ ] Verify retrieval quality with sample questions

### 7) RAG application flow
- [x] Build query pipeline (retrieve -> answer)
- [ ] Add metadata-aware filtering in retrieval
- [ ] End-to-end tests for core RAG flow

### 8) Evaluation
- [x] Choose framework (DeepEval)
- [ ] Define evaluation dataset and metrics
- [ ] Produce a short evaluation report

### 9) Documentation and learning notes
- [ ] Document chunking strategy rationale
- [ ] Document metadata design choices
- [ ] Capture lessons learned

## First milestone
Complete steps 1-2 with a clean architecture scaffold and a passing test harness.
