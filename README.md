# PaperRAG

PaperRAG is a full-stack research paper QA application. Users can sign up, verify their email, upload PDFs, index them, and ask questions over one paper or many papers at once. The app streams answers in markdown, shows the retrieved chunks and retrieval scores used to answer, and persists chat history per user.

For the full system walkthrough, implementation details, and end-to-end flow, see [PROJECT_DETAILS.md](PROJECT_DETAILS.md).

## What It Solves

Research papers are hard to search and compare manually. PaperRAG turns a small paper collection into a searchable workspace where users can:

- upload and manage papers
- query across selected papers
- inspect the evidence behind an answer
- revisit previous chat history

## What Is Built

The current application includes:

- email-verified authentication with JWT-based access
- multi-user paper upload and ownership
- background PDF ingestion and indexing
- hybrid retrieval using BM25 + vector search + reranking
- streamed chat responses from Gemini
- markdown answer rendering in the UI
- retrieval inspection via chunk cards, score table, and referenced papers
- chat persistence per user

## Architecture

```text
Frontend (React + Vite)
  |
  |  HTTP + SSE
  v
Backend API (FastAPI)
  |- Auth routes
  |- Papers routes
  |- Chat routes
  |
  |- SQLite
  |   |- users
  |   |- papers
  |   |- chat_messages
  |
  |- RAG pipeline
      |- PDF loading + cleaning
      |- metadata extraction
      |- chunking
      |- Gemini embeddings
      |- Chroma vector store
      |- BM25 lexical index
      |- RRF merge
      |- reranker
      |- Gemini answer generation
```

## Tech Stack

Backend:

- FastAPI
- SQLite
- JWT (`python-jose`)
- Resend
- LangChain
- ChromaDB
- BM25 (`rank_bm25`)
- Sentence Transformers / Cohere reranker
- Google Gemini embeddings + chat model

Frontend:

- React
- Vite
- TypeScript
- Zustand
- React Router
- React Markdown
- Tailwind + shadcn/ui components

## How Retrieval Works

1. PDFs are loaded, cleaned, chunked, and embedded.
2. Chunks are stored in Chroma with user and paper metadata.
3. A BM25 index is built over the same chunk set.
4. At query time, the app runs BM25 and vector retrieval in parallel.
5. Results are merged with Reciprocal Rank Fusion.
6. A reranker selects the strongest chunks.
7. Gemini answers using only the retrieved context.
8. The UI shows the retrieved chunks and score breakdown for transparency.

## Run Locally

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Required Environment Variables

Repo root `.env`:

```env
GOOGLE_API_KEY=
RESEND_API_KEY=
RESEND_FROM=onboarding@resend.dev
FRONTEND_URL=http://localhost:8080
JWT_SECRET=change-me
JWT_EXPIRE_MINUTES=1440
```

Frontend `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Useful Commands

Rebuild the full vector index:

```bash
python -m scripts.ingest
```

Rebuild BM25:

```bash
python -m scripts.bm25_index
```

Run the CLI version:

```bash
python -m scripts.main
```

## Current Notes

- Uploaded papers are stored in `backend/uploads/`.
- Vector data is stored in `chroma_db/`.
- BM25 artifacts are stored in `bm25.pkl` and `bm25_chunks.pkl`.
- The app currently uses SQLite, which is fine for local development and demos but not ideal for larger production workloads.
- PDF extraction quality still depends on the source PDF, though ingestion now prefers `PyPDFLoader` for cleaner text extraction.
