# RAG Practice

Local practice project for building a RAG app using LangChain, a vector database, and OpenAI multimodal models.
Architecture follows the *Cosmic Python* separation of domain, application, and adapters.

## Setup
1. Create a `.env` file based on `.env.example` and set `OPENAI_API_KEY`.
2. Install dependencies:
   - `python -m pip install -e .[dev,eval]`

## Quick Start (placeholder)
- Ingestion, chunking, and retrieval scripts will live under `scripts/`.
- Tests run with `pytest`.
