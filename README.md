# Research Paper Q&A — RAG

## Summary
- **Problem**: Answer questions across multiple research PDFs with grounded, cited responses.
- **What I Built**: A full-stack RAG system with PDF ingestion, hybrid retrieval, cross-encoder reranking, citation-enforced generation, and a React UI.
- **Tech Stack**: FastAPI, React + Vite, LangChain, ChromaDB, BM25, Groq LLM, Google GenAI embeddings, Resend (email verification).
- **Key Decisions**: Hybrid BM25+vector with RRF; reranking for precision; strict citation validation; email-verified auth for uploads.
- **Run It**: Start backend on `:8000`, frontend on `:8080`, then sign up, verify email, upload PDFs, chat.

## Features
- PDF ingestion with metadata, cleaning, chunking, and Chroma persistence
- BM25 index built from stored chunks
- Hybrid retrieval with RRF merge + cross-encoder reranking
- Citation-enforced generation with validation
- JWT auth + email verification (Resend)
- React UI with library, chat, and retrieval insights

## Project Structure
```
.
├── backend/
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── papers.py
│   │   └── chat.py
│   ├── db.py
│   ├── db_papers.py
│   ├── email_utils.py
│   ├── ingest_pipeline.py
│   ├── ingest_worker.py
│   ├── requirements.txt
│   └── app.db (runtime)
├── frontend/
│   ├── src/
│   └── package.json
├── rag/
│   ├── ingest.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── bm25_index.py
│   └── output_parser.py
├── scripts/
│   └── ingest.py
├── chroma_db/ (runtime)
└── requirements.txt
```

## Setup

### 1) Backend
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install -r requirements.txt
```

Create `.env` in repo root:
```
GROQ_API_KEY=
GOOGLE_API_KEY=
COHERE_API_KEY=
RESEND_API_KEY=
RESEND_FROM=onboarding@resend.dev
FRONTEND_URL=http://localhost:8080
JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=1440
LANGSMITH_TRACING=false
```

Run backend:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

## Usage
1. Sign up in the UI.
2. Verify email via the link (Resend).
3. Upload PDFs.
4. Ask questions in chat.

## Notes
- Resend requires a verified sender. Use `onboarding@resend.dev` if you don’t own a domain.
- The backend SSE `/chat` endpoint streams tokens and returns retrieval metadata.
