# Frontend ↔ Backend Integration Plan

## Overview

The frontend is React (Lovable). The backend is FastAPI. Every UI action maps to a specific API call. This plan covers exactly what endpoints to build, what shape the data takes, and the order to wire things up.

---

## Step 0: FastAPI Project Setup

```
backend/
├── main.py              # FastAPI app + CORS
├── routers/
│   ├── auth.py          # /auth endpoints
│   ├── papers.py        # /papers endpoints
│   └── chat.py          # /chat endpoint (SSE)
├── ingest.py
├── bm25_index.py
├── retriever.py
├── reranker.py
├── output_parser.py
├── chroma_db/
└── .env
```

**CORS — required for React to talk to FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Step 1: Auth Endpoints

The frontend has sign in + sign up pages. Backend needs JWT-based auth.

### POST `/auth/register`
```json
// Request
{ "full_name": "Pranay", "email": "p@neu.edu", "password": "pass123" }

// Response
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### POST `/auth/login`
```json
// Request
{ "email": "p@neu.edu", "password": "pass123" }

// Response (only if email is verified)
{ "access_token": "eyJ...", "token_type": "bearer" }

// Response (if email not verified)
// HTTP 403
{ "detail": "Email not verified. Check your inbox." }
```

**Frontend wiring:**
- On successful login/register → store JWT in memory (Zustand) + `sessionStorage`
- Attach JWT to every subsequent request: `Authorization: Bearer <token>`
- On 401 response from any endpoint → redirect to `/login`
- On 403 with "Email not verified" → show a banner with a "Resend verification email" button

**Backend implementation:**
- Store users in SQLite (`users` table: id, name, email, hashed_password, is_verified, verification_token)
- Use `passlib` for password hashing, `python-jose` for JWT
- All other endpoints use a `get_current_user` dependency that validates the token

---

## Step 1.5: Email Verification Flow

### On Register (`POST /auth/register`):
1. Create user with `is_verified = False`
2. Generate a random token: `secrets.token_urlsafe(32)`
3. Store token in `users.verification_token`
4. Send verification email with link: `http://localhost:5173/verify?token=<token>`
5. Return `{ "message": "Check your email to verify your account." }` — do NOT return a JWT yet

### GET `/auth/verify?token=<token>`
```json
// Response (valid token)
{ "access_token": "eyJ...", "token_type": "bearer" }

// Response (invalid/expired token)
// HTTP 400
{ "detail": "Invalid or expired verification token." }
```

Backend sets `is_verified = True`, clears `verification_token`, returns JWT.

### POST `/auth/resend-verification`
```json
// Request
{ "email": "p@neu.edu" }

// Response
{ "message": "Verification email resent." }
```

Rate limit this to 3 attempts per hour per email to prevent abuse.

**Frontend wiring:**
- `/verify` route in React reads `?token=` from URL → hits `GET /auth/verify` → on success stores JWT and redirects to `/`
- If token invalid → show error page with link back to sign in

**Email provider:** Use [Resend](https://resend.com) — free tier is 3000 emails/month, dead simple API:
```python
import resend
resend.api_key = os.environ["RESEND_API_KEY"]

resend.Emails.send({
    "from": "noreply@yourdomain.com",
    "to": user.email,
    "subject": "Verify your PaperRAG account",
    "html": f"<a href='{verification_url}'>Click here to verify your email</a>"
})
```

**Upload gate:** Before ingestion, check both conditions:
```python
if not current_user.is_verified:
    raise HTTPException(status_code=403, detail="Verify your email before uploading.")
if existing_paper_count >= 1:
    raise HTTPException(status_code=403, detail="Free tier limit: 1 document per account.")
```

---

## Step 2: Paper Library Endpoints

### GET `/papers`
Returns all papers ingested by the current user.

```json
// Response
[
  {
    "id": "uuid",
    "title": "Attention Is All You Need",
    "authors": "Vaswani et al.",
    "year": 2017,
    "source_file": "attention.pdf",
    "status": "indexed"   // "indexing" | "indexed" | "failed"
  }
]
```

**Frontend wiring:**
- Called on app load → populates left sidebar paper list
- Status dot color: green = indexed, yellow = indexing, red = failed

**Backend implementation:**
- Store paper metadata in SQLite (`papers` table: id, user_id, title, authors, year, source_file, status)
- Filter by `user_id` from JWT — this is how per-user libraries work

---

### POST `/papers/upload`
Accepts one or more PDF files. Triggers ingestion pipeline.

```
// Request: multipart/form-data
files: [attention.pdf, bert.pdf]

// Response (immediate, before indexing completes)
[
  { "id": "uuid1", "source_file": "attention.pdf", "status": "indexing" },
  { "id": "uuid2", "source_file": "bert.pdf", "status": "indexing" }
]
```

**Frontend wiring:**
- On drop/browse → POST to `/papers/upload`
- Immediately add papers to sidebar with yellow dot
- Poll `GET /papers/{id}` every 2 seconds until status = "indexed" → switch to green dot

**Backend implementation:**
- Save PDF to disk
- Run ingestion in a background task (`fastapi.BackgroundTasks`)
- Update paper status in SQLite when ingestion completes or fails
- Extract title/authors from PDF metadata using `PyMuPDF`: `doc.metadata["title"]`, `doc.metadata["author"]`

---

### DELETE `/papers/{id}`
Removes a paper from the library and from ChromaDB.

```json
// Response
{ "deleted": true }
```

**Frontend wiring:**
- Trash icon click → DELETE → remove paper from sidebar state

**Backend implementation:**
- Delete all ChromaDB chunks where `metadata.source_file == paper.source_file AND metadata.user_id == current_user.id`
- Delete paper row from SQLite
- Rebuild BM25 index after deletion

---

## Step 3: Chat Endpoint (SSE)

This is the most critical endpoint. It drives the entire center + right panel.

### POST `/chat`
```json
// Request
{
  "query": "How do Transformers differ from previous sequence models?",
  "paper_ids": ["uuid1", "uuid2", "uuid3", "uuid4"],
  "chat_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response: Server-Sent Events stream**

Three event types in order:

```
event: token
data: "Transformers"

event: token
data: " represent"

event: token
data: " a fundamental..."

// ... more token events ...

event: metadata
data: {
  "citations": [
    { "ref": "Vaswani et al., 2017", "source_file": "attention.pdf" }
  ],
  "chunks": [
    {
      "content": "The dominant sequence transduction models...",
      "title": "Attention Is All You Need",
      "authors": "Vaswani et al.",
      "year": 2017,
      "source_file": "attention.pdf",
      "bm25_rank": 2,
      "vector_rank": 1,
      "rrf_score": 0.031,
      "rerank_score": 0.94
    }
  ]
}

event: done
data: {}
```

**Frontend wiring:**
```javascript
const res = await fetch("/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`
  },
  body: JSON.stringify({ query, paper_ids: selectedPaperIds, chat_history })
});

const reader = res.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split("\n");
  for (const line of lines) {
    if (line.startsWith("event: token")) {
      // append token to assistant message bubble
    }
    if (line.startsWith("event: metadata")) {
      const metadata = JSON.parse(line.replace("data: ", ""));
      // render citation chips below message
      // populate right sidebar chunks + scores
    }
  }
}
```

**Backend implementation (FastAPI SSE):**
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
async def chat(request: ChatRequest, current_user = Depends(get_current_user)):
    async def generate():
        # 1. Retrieve + rerank
        chunks = hybrid_retrieve(request.query, request.paper_ids, current_user.id)
        reranked = rerank(request.query, chunks)

        # 2. Stream LLM tokens
        for chunk in llm.stream(build_messages(request, reranked)):
            yield f"event: token\ndata: {chunk.content}\n\n"

        # 3. Send metadata after stream ends
        metadata = build_metadata(reranked)
        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Step 4: Citation Chip → Chunk Highlight

Once metadata arrives, wire citation chips to right sidebar:

```javascript
// Zustand store
{
  highlightedChunkIndex: null,
  setHighlightedChunk: (index) => set({ highlightedChunkIndex: index })
}

// CitationChip onClick
<span onClick={() => setHighlightedChunk(citationIndex)}>
  [Vaswani et al., 2017]
</span>

// ChunkCard in right sidebar
<div className={highlightedChunkIndex === index ? "ring-2 ring-amber-400" : ""}>
  ...
</div>
```

---

## Step 5: Score Breakdown Table

Each chunk card in the right sidebar should expand to show:

| Metric | Value |
|---|---|
| BM25 Rank | 2 |
| Vector Rank | 1 |
| RRF Score | 0.031 |
| Rerank Score | 0.94 |

This data already comes in the `metadata` SSE event — just render it in a collapsible inside each chunk card.

---

## Integration Order (what to build first)

1. FastAPI skeleton + CORS
2. Auth endpoints + JWT middleware
3. SQLite schema (users, papers tables)
4. `GET /papers` + `DELETE /papers/{id}`
5. `POST /papers/upload` + background ingestion + status polling
6. `POST /chat` SSE endpoint
7. Citation chip → chunk highlight
8. Score breakdown table in chunk cards

---

## Environment Variables

```
# backend/.env
GROQ_API_KEY=
GOOGLE_API_KEY=
JWT_SECRET=your_random_secret
JWT_EXPIRE_MINUTES=1440

# frontend/.env
VITE_API_URL=http://localhost:8000
```

All fetch calls in React should use `import.meta.env.VITE_API_URL` as the base URL so switching from local to deployed backend is a one-line change.
