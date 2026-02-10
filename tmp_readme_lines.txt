51: │   ├── models.py          # Core dataclasses (Document, Chunk, TableRef, QueryResult)
52: │   └── ports.py           # Abstract interfaces (VectorIndex, Embedder)
60:     └── use_cases.py       # Business logic (IngestUseCase, QueryUseCase)
71: ├── test_table_models.py
345: ### `src/rag_practice/domain/models.py`
400: ### `src/rag_practice/application/use_cases.py`
557: pytest tests/test_table_models.py -v