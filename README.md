# Research Paper Q&A - RAG

A local RAG pipeline for answering questions across multiple research PDFs using hybrid retrieval (BM25 + vector), cross‑encoder reranking, and citation‑enforced generation.

## Features
- PDF ingestion with metadata, cleaning, chunking, and Chroma persistence
- BM25 index built from stored chunks
- Hybrid retrieval with RRF merge
- Cross‑encoder reranking (Cohere or local fallback)
- Citation‑enforced generation with validation

## Project Structure
```
.
├── scripts/
│   ├── ingest.py
│   ├── main.py
│   ├── bm25_index.py
│   └── verify_week1.py
├── rag/
│   ├── __init__.py
│   ├── tools.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── bm25_index.py
│   ├── output_parser.py
│   └── verify_week1.py
├── data/
├── chroma_db/
├── bm25.pkl
├── bm25_chunks.pkl
├── .env
└── requirements.txt
```

## Setup
1. Install dependencies
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`
```
GROQ_API_KEY=
GOOGLE_API_KEY=
COHERE_API_KEY=
LANGSMITH_TRACING=false
```

3. Add PDFs to `./data`

4. Run ingestion and indexing
```bash
python scripts/ingest.py
python scripts/bm25_index.py
```

5. Start the CLI
```bash
python scripts/main.py
```

## Notes
- Cohere reranking is optional. If `COHERE_API_KEY` is not set, a local cross‑encoder is used instead.