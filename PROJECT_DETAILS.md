# PaperRAG: Detailed Project Reference

## 1. What This Project Is

PaperRAG is a full-stack research paper question-answering application. It lets a user:

- create an account
- verify the account by email
- upload PDF papers
- index those papers into a retrieval system
- ask questions against one paper or many papers at once
- receive streamed answers in markdown
- inspect the retrieved chunks and retrieval scores used to generate each answer
- persist chat history per user

At a high level, it is a multi-user Retrieval-Augmented Generation (RAG) system with a React frontend, a FastAPI backend, a SQLite app database, a Chroma vector store, a BM25 lexical index, and a reranking layer.

---

## 2. Core User-Facing Capabilities

### Authentication

The app supports:

- account signup with full name, email, and password
- email verification via Resend
- login with JWT access tokens
- route protection in the frontend
- logout from the main chat screen

Important implementation detail:

- only verified users can access authenticated routes
- JWTs are stored in browser `sessionStorage`

### Paper Management

The app supports:

- uploading one or more PDF files
- duplicate detection by original filename per user
- background indexing after upload
- paper status tracking (`indexing`, `indexed`, `failed`)
- listing all papers owned by the logged-in user
- deleting papers
- reindexing papers
- selecting or deselecting papers for query scope
- cross-paper querying when multiple papers are selected

### Chat / QA

The app supports:

- streaming responses over Server-Sent Events (SSE)
- markdown rendering for answers
- follow-up question context
- paper-selection-aware querying
- persisted chat history per user
- clearing chat history
- answer-side source citation markers mapped to retrieved chunks

### Retrieval Inspection

The right sidebar exposes:

- retrieved chunk cards
- score breakdown table
- referenced papers summary
- chunk highlighting when a citation badge is clicked in the answer

---

## 3. High-Level Architecture

The project is split into four main parts:

### Frontend

Location: `frontend/`

Responsibilities:

- authentication screens
- paper upload UI
- paper selection UI
- chat UI
- markdown answer rendering
- retrieval evidence visualization
- session token handling
- local app state management with Zustand

### Backend API

Location: `backend/`

Responsibilities:

- auth routes
- paper upload/list/delete/reindex routes
- chat streaming routes
- chat history persistence
- JWT validation
- email verification
- orchestrating ingestion in background tasks

### RAG Layer

Location: `rag/`

Responsibilities:

- PDF loading
- text cleanup
- metadata extraction
- chunking
- vector indexing in Chroma
- BM25 index build/search
- hybrid retrieval
- reranking

### Utility / CLI Scripts

Location: `scripts/`

Responsibilities:

- full re-ingest from the local `data/` folder
- BM25 rebuild
- CLI-based QA against the same RAG stack

---

## 4. Backend in Detail

### 4.1 FastAPI App

File: `backend/main.py`

The backend:

- loads environment variables from the repo root `.env`
- configures CORS
- mounts three routers:
  - `/auth`
  - `/papers`
  - `/chat`
- exposes a lightweight `/health` endpoint

### 4.2 Auth System

Key files:

- `backend/routers/auth.py`
- `backend/auth_utils.py`
- `backend/deps.py`
- `backend/email_utils.py`
- `backend/db.py`
- `backend/schemas.py`

What it does:

- creates user accounts in SQLite
- hashes passwords with `pbkdf2_sha256`
- generates email verification tokens
- sends verification emails via Resend
- verifies tokens and marks users as verified
- issues JWT access tokens
- validates bearer tokens for protected routes

Additional behavior:

- signup returns a generic success message if the email already exists
- resend verification has a simple in-memory rate limit:
  - 3 requests
  - per email
  - per 1 hour window

### 4.3 Paper Management API

Key files:

- `backend/routers/papers.py`
- `backend/db_papers.py`
- `backend/ingest_pipeline.py`
- `backend/ingest_worker.py`

What it does:

- returns all papers for the current user
- accepts multipart PDF uploads
- checks duplicate filenames for the same user
- saves uploaded files into `backend/uploads/`
- extracts initial metadata before indexing
- inserts a `papers` row with status `indexing`
- launches background ingestion for each paper
- updates paper status to `indexed` or `failed`
- deletes papers and their vector/BM25 entries
- supports per-paper reindexing

Data recorded per paper:

- `id`
- `user_id`
- `title`
- `authors`
- `year`
- `source_file`
- `status`
- `created_at`

### 4.4 Chat API

Key file:

- `backend/routers/chat.py`

The chat API provides:

- `GET /chat/history`
- `DELETE /chat/history`
- `POST /chat/save`
- `POST /chat`
- `GET /chat/debug-filters`

`POST /chat` does the following:

1. receives the user query, selected paper IDs, and frontend chat history
2. runs hybrid retrieval scoped to the current user and selected papers
3. constructs a numbered context block from retrieved chunks
4. sends that context to Gemini (`gemini-2.5-flash`)
5. streams tokens back over SSE
6. sends a final metadata event containing retrieved chunk details and retrieval scores

Prompt behavior:

- restricts answers to the provided context
- tells the model not to reuse earlier assistant content if paper selection changed
- asks for markdown structure
- asks for inline numeric citations like `[1]`
- asks for short bullet-based answers with headings and bold text

Streaming implementation detail:

- token chunks are JSON-encoded before being sent through SSE so markdown markers and newlines are preserved

Chat persistence:

- user messages are saved with `/chat/save`
- assistant messages are saved after the stream completes
- chunk metadata is saved alongside assistant messages

### 4.5 SQLite Persistence

Primary database file:

- `backend/app.db`

Tables in current use:

- `users`
- `papers`
- `chat_messages`

SQLite behavior:

- uses WAL mode
- stores user, paper, and chat state in the same DB

---

## 5. RAG Pipeline in Detail

### 5.1 Ingestion

Key file:

- `rag/ingest.py`

Current ingestion flow:

1. collect PDF files from explicit paths or from `data/`
2. load each PDF
3. strip repeated headers and footers
4. normalize text
5. extract document metadata
6. split into chunks
7. embed chunks
8. write chunks into Chroma
9. rebuild BM25
10. invalidate vector/BM25 caches

Current loader strategy:

- prefers `PyPDFLoader`
- falls back to `PDFPlumberLoader`

This was introduced because `PyPDFLoader` extracts cleaner word spacing for some papers than `pdfplumber`.

### 5.2 Text Cleaning

`_clean_text()` currently handles:

- ligature normalization
- non-printable character removal
- some arrow-symbol repair
- spacing repair for camelCase-like joins
- parenthesis spacing cleanup
- whitespace normalization

### 5.3 Metadata Extraction

The ingestion step attempts to infer:

- title
- authors
- publication year

It uses heuristics on early lines of the first page rather than a dedicated metadata parser.

### 5.4 Chunking

Current chunk settings:

- chunk size: `1500`
- chunk overlap: `300`

Chunk IDs are generated and stored in metadata. Each chunk also carries:

- source file name
- absolute source path
- user ID
- paper ID
- title
- authors
- year

### 5.5 Vector Store

Vector backend:

- ChromaDB

Embedding model:

- `models/gemini-embedding-001`

Persisted data lives in:

- `chroma_db/`

### 5.6 BM25 Index

Key file:

- `rag/bm25_index.py`

What it does:

- loads all chunks from Chroma
- tokenizes and removes stopwords
- builds a `BM25Okapi` index
- saves the BM25 index and chunk list to disk
- supports user-aware and paper-aware filtering at query time

Persisted files:

- `bm25.pkl`
- `bm25_chunks.pkl`

### 5.7 Hybrid Retrieval

Key file:

- `rag/retriever.py`

Current retrieval algorithm:

1. run BM25 search
2. run Chroma vector search with MMR
3. merge both rankings with Reciprocal Rank Fusion (RRF)
4. take the merged candidate pool
5. rerank candidates
6. return reranked docs plus score metadata

Current retrieval constants:

- BM25 top-k: `20`
- vector top-k: `20`
- vector fetch-k: `40`
- MMR lambda: `0.5`
- RRF k: `60`
- merged candidate pool: `40`
- rerank top-n: `20`

Filtering behavior:

- queries are scoped by `user_id`
- if papers are selected, they are additionally scoped by `paper_id IN [...]`

### 5.8 Reranking

Key file:

- `rag/reranker.py`

The app supports two reranker backends:

- Cohere rerank API if `COHERE_API_KEY` is present
- local cross-encoder otherwise

Default local model:

- `cross-encoder/ms-marco-MiniLM-L-6-v2`

This means the app can run without Cohere, but local reranking requires the `sentence-transformers` stack.

### 5.9 Tool Layer and CLI

Key files:

- `rag/tools.py`
- `scripts/main.py`
- `scripts/ingest.py`
- `scripts/bm25_index.py`

The CLI side of the project supports:

- forcing a full ingest
- forcing a BM25 rebuild
- asking questions from the terminal
- basic follow-up handling
- listing ingested sources for ingestion-related questions

---

## 6. Frontend in Detail

### 6.1 App Shell

Key files:

- `frontend/src/App.tsx`
- `frontend/src/pages/Index.tsx`

The frontend:

- uses React Router
- protects `/` with `AuthGuard`
- exposes `/login`, `/signup`, `/verify`
- uses a three-pane desktop layout:
  - left paper library
  - center chat
  - right retrieval info
- uses mobile sheets for sidebars

### 6.2 Session Handling

Key file:

- `frontend/src/lib/api.ts`

What it does:

- stores the auth token in `sessionStorage`
- automatically attaches `Authorization: Bearer <token>`
- clears the token on `401`

### 6.3 Zustand Store

Key file:

- `frontend/src/store/useAppStore.ts`

State tracked in the frontend:

- list of papers
- selected paper IDs
- chat messages
- active retrieved chunks
- currently highlighted chunk
- streaming state

Store actions cover:

- adding/removing papers
- updating paper status
- selecting papers
- appending chat messages
- updating the streaming assistant message
- finalizing assistant messages with chunks
- clearing chat

### 6.4 Auth Pages

Key files:

- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Signup.tsx`
- `frontend/src/pages/Verify.tsx`

What they do:

- signup posts to `/auth/register`
- login posts to `/auth/login`
- verify uses `token` from the URL and calls `/auth/verify`
- successful login or verification stores the access token and routes into the app

### 6.5 Left Sidebar

Key files:

- `frontend/src/components/LeftSidebar.tsx`
- `frontend/src/components/PaperCard.tsx`
- `frontend/src/components/UploadZone.tsx`

What it does:

- supports PDF upload
- polls `/papers` while files are indexing
- auto-selects indexed papers
- shows paper count
- supports select all / deselect all
- lets the user delete papers
- currently displays uploaded filenames in the library list

### 6.6 Chat Panel

Key files:

- `frontend/src/components/ChatTopBar.tsx`
- `frontend/src/components/MessageThread.tsx`
- `frontend/src/components/InputBar.tsx`
- `frontend/src/components/AssistantMessage.tsx`

What it does:

- shows how many papers are currently in query scope
- allows clearing chat
- supports logout
- streams assistant tokens from `/chat`
- persists both user and assistant messages through `/chat/save`
- restores chat history from `/chat/history`
- inserts a small system message when paper selection changes

Markdown behavior:

- assistant output is rendered with `react-markdown`
- `remark-gfm` is enabled
- citation markers like `[3]` are converted into clickable inline badges
- the renderer includes a small markdown repair pass for malformed heading lines

### 6.7 Retrieval Info Sidebar

Key files:

- `frontend/src/components/RightSidebar.tsx`
- `frontend/src/components/ChunkCard.tsx`
- `frontend/src/components/ScoreBreakdownTable.tsx`
- `frontend/src/components/ReferencedPapersList.tsx`

What it shows:

- the retrieved chunks for the latest assistant response
- BM25 rank
- vector rank
- RRF score
- rerank score
- list of distinct papers referenced by those chunks

The citation badges in the assistant answer can scroll and highlight the associated chunk card in this sidebar.

---

## 7. End-to-End Flows

### 7.1 Signup and Verification Flow

1. user signs up in the frontend
2. backend creates a user row with `is_verified = 0`
3. backend generates a verification token
4. Resend sends a verification email with a frontend `/verify` link
5. user opens the link
6. frontend calls backend `/auth/verify`
7. backend marks the user verified and returns a JWT
8. frontend stores the JWT and navigates to the app

### 7.2 Paper Upload and Indexing Flow

1. user uploads PDFs from the left sidebar
2. backend checks duplicate filenames for that user
3. files are copied to `backend/uploads/` with UUID-prefixed names
4. metadata is extracted immediately for initial DB insertion
5. a `papers` row is inserted with status `indexing`
6. a background task runs ingestion
7. ingestion loads the PDF, cleans text, chunks it, embeds it, and stores chunks in Chroma
8. BM25 is rebuilt
9. paper status becomes `indexed` or `failed`
10. frontend polling updates the UI

### 7.3 Question Answering Flow

1. user selects one or more papers
2. frontend sends the query, selected `paper_ids`, and filtered chat history
3. backend runs hybrid retrieval scoped to that user and paper set
4. retrieved chunks are formatted into a numbered context block
5. Gemini generates an answer
6. tokens stream back over SSE
7. frontend appends tokens into the current assistant message
8. backend sends a final metadata event containing retrieved chunks and scores
9. frontend finalizes the message, updates the right sidebar, and persists the assistant message

### 7.4 Reindex Flow

1. user triggers reindex for a paper
2. backend removes all chunks with that `paper_id` from Chroma
3. BM25 and vector caches are invalidated
4. the original uploaded file is found on disk
5. ingestion runs again in the background
6. paper status updates after completion

### 7.5 Delete Flow

1. user deletes a paper
2. backend removes the paper’s chunks from Chroma
3. backend rebuilds BM25
4. backend deletes the paper row from SQLite
5. frontend removes the paper from local state

---

## 8. Current API Surface

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/verify?token=...`
- `POST /auth/resend-verification`

### Papers

- `GET /papers`
- `POST /papers/upload`
- `POST /papers/{paper_id}/reindex`
- `DELETE /papers/{paper_id}`

### Chat

- `POST /chat`
- `GET /chat/history`
- `DELETE /chat/history`
- `POST /chat/save`
- `GET /chat/debug-filters`

### Health

- `GET /health`

---

## 9. Data and Runtime Artifacts

Persistent or semi-persistent artifacts in the repo layout:

- `backend/app.db`
- `backend/uploads/`
- `chroma_db/`
- `bm25.pkl`
- `bm25_chunks.pkl`

What they contain:

- `backend/app.db`: users, papers, chat messages
- `backend/uploads/`: uploaded source PDFs with UUID-prefixed filenames
- `chroma_db/`: vectorized chunk store
- `bm25.pkl`: serialized BM25 model
- `bm25_chunks.pkl`: serialized chunk objects used by BM25

---

## 10. Environment Variables

The current code expects or supports these variables:

- `GOOGLE_API_KEY`
- `COHERE_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM`
- `FRONTEND_URL`
- `JWT_SECRET`
- `JWT_EXPIRE_MINUTES`
- `DB_PATH`
- `CORS_ORIGINS`
- `VITE_API_URL` for the frontend

Behavior notes:

- `JWT_SECRET` falls back to an insecure development default if not set
- `COHERE_API_KEY` is optional because the reranker can run locally
- `FRONTEND_URL` determines where verification links point

---

## 11. Scripts and Operational Commands

### Backend

Run:

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### Frontend

Run:

```bash
cd frontend
npm run dev
```

### Full Re-Ingest

```bash
python -m scripts.ingest
```

### Rebuild BM25

```bash
python -m scripts.bm25_index
```

### CLI QA

```bash
python -m scripts.main
```

---

## 12. Engineering Decisions Worth Noting

### Hybrid Retrieval Instead of Vector-Only

The system uses both:

- BM25 for keyword/exact-term recall
- embeddings for semantic recall

This improves robustness on technical queries where exact terminology matters.

### RRF Merge

BM25 and vector results are fused with Reciprocal Rank Fusion instead of using one source as a hard filter. That reduces the chance that one weak scorer dominates retrieval.

### Reranking

A reranker is used after hybrid retrieval to improve final evidence quality. This is important because the merged candidate set can still contain weak chunks.

### Background Ingestion

Uploads return immediately with `indexing` status. Chunking, embedding, and index rebuilds happen in background tasks so the upload UI stays responsive.

### User-Scoped Retrieval

Paper ownership is enforced in retrieval filters using `user_id`, and optional `paper_id` filters narrow retrieval to the selected paper set.

### Chat Persistence

Chat history is stored server-side, not only in browser state. Reloading the main app restores previous messages and attached chunk metadata.

---

## 13. Known Limitations / Current Gaps

These are present in the current implementation:

- SQLite is used for the main app database, which is simple but not ideal for production multi-instance deployments.
- BM25 rebuild currently happens eagerly after ingestion changes, which is simple but can become expensive as the corpus grows.
- The retrieval debug endpoint is still exposed and looks intended for troubleshooting rather than production use.
- Metadata extraction is heuristic and can misread titles/authors on difficult PDFs.
- Chunk text quality still depends heavily on PDF extraction quality.
- The chat prompt still asks the model to cite numeric chunk references inline.
- The current auth/session model uses `sessionStorage`, so sessions do not survive browser session resets.
- There is no true background worker queue like Celery/RQ yet. FastAPI background tasks are used instead.
- The resend verification limiter is in-memory, so it resets on process restart and is not distributed.

---

## 14. What This Project Demonstrates

This project demonstrates:

- full-stack product wiring, not just an isolated RAG notebook
- authenticated multi-user document ownership
- end-to-end PDF ingestion and retrieval
- hybrid search with BM25 + vector + rerank
- streamed LLM responses with markdown rendering
- retrieval introspection in the UI
- practical operational choices around persistence and indexing

In short, this is not just a chat frontend attached to an LLM. It is a complete document QA application with user accounts, file lifecycle management, retrieval infrastructure, streaming responses, and evidence inspection.
