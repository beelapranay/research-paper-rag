# Bug Fixes Changelog

A total of **46 bugs** were identified and fixed across the entire codebase, spanning the FastAPI backend, the RAG pipeline, and the React/TypeScript frontend.

---

## Table of Contents

- [Critical Fixes (10)](#critical-fixes)
- [High Priority Fixes (13)](#high-priority-fixes)
- [Medium Priority Fixes (12)](#medium-priority-fixes)
- [Low Priority Fixes (9)](#low-priority-fixes)
- [Files Modified](#files-modified)

---

## Critical Fixes

### 1. Hardcoded JWT Secret — `backend/config.py`

**Bug:** `JWT_SECRET` defaulted to the string `"dev-secret-change"` if the environment variable was not set. In production, anyone aware of this default could forge valid JWT tokens and impersonate any user.

**Fix:** The module now checks whether `JWT_SECRET` is set. If missing, it emits a loud `warnings.warn()` before falling back to the insecure default, making it impossible to silently deploy without a real secret.

---

### 2. JWT Expiration Not a Unix Timestamp — `backend/auth_utils.py`

**Bug:** The `exp` claim in JWT tokens was set to a Python `datetime` object. The `python-jose` library may not reliably interpret this, causing tokens to either never expire or behave unpredictably.

**Fix:** Changed `"exp": expire` to `"exp": int(expire.timestamp())`, ensuring a proper Unix epoch integer is used.

---

### 3. Broken Import Path — `rag/tools.py`

**Bug:** `from ingest import build_index` used a bare module name that does not resolve when the package is imported as `rag.ingest`. This caused a runtime `ModuleNotFoundError`.

**Fix:** Changed to `from rag.ingest import build_index`.

---

### 4. Unhandled Pickle Load Errors — `rag/bm25_index.py`

**Bug:** `pickle.load()` in `_load_bm25()` had no error handling. Corrupted or truncated index files would crash the service with an unhandled `EOFError` or `UnpicklingError`.

**Fix:** Wrapped both pickle loads in a `try/except` block catching `pickle.UnpicklingError`, `EOFError`, `ValueError`, and `OSError`. On failure, a clear `RuntimeError` is raised instructing the user to delete the corrupt files and re-run ingestion.

---

### 5. File Descriptor Leak in Upload — `backend/ingest_worker.py`

**Bug:** `save_uploads()` did not close `file.file` (the uploaded file's `SpooledTemporaryFile`) after copying. If `shutil.copyfileobj()` raised an exception partway through a batch, subsequent file handles would leak.

**Fix:** Added a `try/except/finally` block that always calls `file.file.close()`. Also added `logger.exception()` for diagnostics on failure.

---

### 6. Memory Leak in useToast Hook — `frontend/src/hooks/use-toast.ts`

**Bug:** The `useEffect` that registers a listener had `[state]` in its dependency array. Because `state` changes on every toast, a new `setState` function was pushed to the global `listeners` array on every render. The cleanup could never find the old reference, so listeners accumulated indefinitely, causing exponential performance degradation.

**Fix:** Changed the dependency array from `[state]` to `[]` so the listener is registered once on mount and removed once on unmount.

---

### 7. Unhandled JSON.parse in Stream — `frontend/src/components/InputBar.tsx`

**Bug:** `JSON.parse(dataLine.replace("data: ", ""))` inside the streaming loop had no error handling. Malformed server JSON would throw, breaking out of the loop without resetting `isStreaming`, permanently locking the UI.

**Fix:** Wrapped the `JSON.parse` call in its own `try/catch`. On failure, an error is logged to the console and streaming continues gracefully.

---

### 8. Stream Reader Never Cancelled — `frontend/src/components/InputBar.tsx`

**Bug:** If an error occurred mid-stream or the user navigated away, the `ReadableStreamDefaultReader` was never cancelled. The abandoned stream would continue consuming server data in the background, wasting bandwidth and holding connections open.

**Fix:** Wrapped the entire streaming `while` loop in `try/catch/finally`. The `finally` block always calls `reader.cancel()`. On error, the UI is updated with the partial text and `isStreaming` is reset.

---

### 9. Dangling setTimeout on Unmount — `frontend/src/components/LeftSidebar.tsx`

**Bug:** `setTimeout(poll, 2000)` was scheduled inside `handleUpload` with no cleanup. If the component unmounted before the timeout fired, the callback would execute and call `setState` on an unmounted component, causing React warnings and memory leaks. Multiple uploads would also stack up independent timeouts.

**Fix:** Introduced a `pollTimeoutRef` (via `useRef`) to track the active timeout. A `useEffect` cleanup function clears it on unmount. Before scheduling a new poll, any existing timeout is cleared first.

---

### 10. State Update After Unmount — `frontend/src/pages/Index.tsx`

**Bug:** The `loadPapers` async function inside `useEffect` had no cancellation mechanism. If the user navigated away before the API responded, `setPapers(data)` would fire on an unmounted component.

**Fix:** Added a `cancelled` flag that is set to `true` in the effect's cleanup function. All state updates check `if (!cancelled)` before executing.

---

## High Priority Fixes

### 11. Race Condition in Registration — `backend/routers/auth.py`

**Bug:** Between the `get_user_by_email()` check and the `create_user()` call, a concurrent request with the same email could slip through, creating duplicate accounts.

**Fix:** Wrapped `create_user()` in a `try/except sqlite3.IntegrityError` block. The `users` table has a `UNIQUE` constraint on `email`, so the database itself rejects the duplicate even if the application-level check passes.

---

### 12. Silent Data Loss with zip() — `backend/routers/papers.py`

**Bug:** `zip(saved_paths, files)` would silently drop extras if the two lists differed in length. If `save_uploads()` partially failed, some files would get metadata but no saved file, or vice versa.

**Fix:** Added a length assertion after `save_uploads()`: if `len(saved_paths) != len(files)`, a 500 error is raised immediately.

---

### 13. DELETE Always Returned Success — `backend/routers/papers.py`

**Bug:** The `delete_paper` endpoint returned `{"deleted": True}` without checking whether any row was actually deleted. A request to delete a non-existent paper or another user's paper would appear successful.

**Fix:** Now checks `cur.rowcount`. If zero rows were affected, a 404 `"Paper not found."` is returned.

---

### 14. Missing Null Check on Credentials — `backend/deps.py`

**Bug:** If no `Authorization` header was provided, `credentials` could be `None`, and `credentials.credentials` would throw an `AttributeError`, resulting in an HTTP 500 instead of a proper 401.

**Fix:** Added an explicit `if not credentials` check at the top of `get_current_user()` that raises a 401.

---

### 15. Race Condition in Email Verification — `backend/routers/auth.py` + `backend/db.py`

**Bug:** Between `get_user_by_token()` and `mark_verified()`, a concurrent request could verify the same token twice. There was no atomicity guarantee.

**Fix:** `mark_verified()` now takes the `token` as an optional parameter and uses `WHERE id = ? AND verification_token = ?` in a single UPDATE statement. It returns a `bool` indicating whether any row was updated. The verify endpoint checks this return value and rejects stale tokens.

---

### 16. Unhandled Email Send Exception — `backend/email_utils.py`

**Bug:** `resend.Emails.send()` could throw any exception, which would propagate as an uncontrolled 500 error with no context.

**Fix:** Wrapped the call in `try/except`, re-raising as `RuntimeError` with the recipient email and original error message for clear diagnostics.

---

### 17. Inconsistent Deduplication — `rag/ingest.py`

**Bug:** When checking whether a PDF was already indexed, the code used `str(user_id or "")`. If `user_id` was `None` on the first ingestion but a string on the second, the comparison would fail and the same file would be ingested twice.

**Fix:** Normalized `user_id` to a consistent `uid_str = str(user_id) if user_id else ""` before the comparison.

---

### 18. Incomplete Score Map After Rerank — `rag/retriever.py`

**Bug:** The score map was built by iterating all `merged_docs` by index and checking membership in `rerank_scores`. This approach could miss documents or create misaligned key-score pairs.

**Fix:** Changed the loop to iterate `rerank_scores.items()` directly, building the score map from the authoritative source: `for idx, score in rerank_scores.items(): score_map[_doc_key(merged_docs[idx])] = score`.

---

### 19. Weak Year Parsing — `backend/routers/papers.py`

**Bug:** `year_str.isdigit()` rejects valid year strings like `"2024"` with leading/trailing whitespace, and silently sets the year to 0 for anything non-digit. It also can't handle strings like `"-2024"`.

**Fix:** Replaced with `try: int(year_str)` / `except (ValueError, TypeError): year = 0`.

---

### 20–21. Unsafe Array Access in Store — `frontend/src/store/useAppStore.ts`

**Bug:** Both `updateLastAssistantMessage` and `finalizeAssistantMessage` accessed `msgs[msgs.length - 1]` without checking if the array was empty. When empty, `msgs.length - 1` equals `-1`, and `msgs[-1]` is `undefined` in JavaScript — a logic error that would silently do nothing.

**Fix:** Added `if (msgs.length === 0) return { messages: msgs }` (with appropriate extra state for `finalize`) as an early return in both functions.

---

### 22. Unvalidated API Response — `frontend/src/components/LeftSidebar.tsx`

**Bug:** After upload, `created.forEach()` was called without verifying that `created` was actually an array. If the server returned `null`, a string, or an object, `forEach` would throw `TypeError`.

**Fix:** Added `if (!Array.isArray(created))` check that shows a toast and returns early.

---

### 23. Polling Runs Only Once — `frontend/src/components/LeftSidebar.tsx`

**Bug:** `setTimeout(poll, 2000)` ran the poll function exactly once. If paper indexing took longer than 2 seconds, the UI would show "processing" forever.

**Fix:** (Fixed as part of Critical #9) The poll function now checks `data.some(p => p.status === "processing")` and schedules another poll if any papers are still processing.

---

## Medium Priority Fixes

### 24. Retrieval Failure Crashes Streaming — `backend/routers/chat.py`

**Bug:** If `hybrid_retrieve()` threw an exception (e.g., Chroma DB not found, embedding API down), the sync generator would crash with an unhandled error. The client would receive a broken stream with no useful message.

**Fix:** Wrapped `hybrid_retrieve()` in a `try/except`. On failure, the generator yields an error message as a stream token and a `done` event, then returns cleanly. Added `logger.exception()` for server-side diagnostics.

---

### 25. No Transaction Isolation — `backend/db.py`

**Bug:** `sqlite3.connect()` was called with default settings. Under concurrent load, multiple writers could cause `database is locked` errors or dirty reads.

**Fix:** Added `timeout=10` (wait up to 10s for locks) and `PRAGMA journal_mode=WAL` (Write-Ahead Logging), which allows concurrent readers and a single writer without blocking.

---

### 26. Deleted/Unverified Users Could Access System — `backend/deps.py`

**Bug:** `get_current_user()` only checked that the user existed in the database. A user whose email was not yet verified, or who was logically deleted, could still access all protected endpoints using an existing JWT.

**Fix:** Added `if not user["is_verified"]: raise HTTPException(status_code=403, detail="Email not verified")` after the user lookup.

---

### 27. Conditional persist() Call — `rag/ingest.py`

**Bug:** `if hasattr(vectorstore, "persist"): vectorstore.persist()` was unreliable. Newer versions of Chroma auto-persist when `persist_directory` is set, and the `hasattr` check could silently skip persistence on older versions where it was needed.

**Fix:** Removed the `hasattr` guard entirely. Chroma auto-persists when a `persist_directory` is provided.

---

### 28. Silent Content Filtering — `rag/ingest.py`

**Bug:** Documents with 100 or fewer characters after cleaning were silently dropped. Users had no way to know that content was being discarded.

**Fix:** Added `logger.info("Dropped %d document(s) with <=100 characters after cleaning.", dropped)` so the count is visible in logs.

---

### 29. No Error Handling on list_papers Query — `backend/routers/papers.py`

**Bug:** Any database error in `list_papers` would propagate as a raw 500 error with a SQLite traceback visible to the client.

**Fix:** Wrapped the query in `try/except` with `logger.exception()` and a clean `HTTPException(status_code=500, detail="Failed to load papers.")`.

---

### 30. Corrupt Chroma DB Causes Unhandled Crash — `rag/retriever.py`

**Bug:** If the Chroma DB files were corrupted or incompatible, `_load_vectorstore()` would throw an unhandled exception, crashing the retrieval path.

**Fix:** Wrapped `_load_vectorstore()` in `try/except`. On failure, logs the exception and raises a clear `RuntimeError("Vectorstore is corrupted or unreadable: ...")`.

---

### 31. Ingestion Exception Swallowed Silently — `backend/ingest_worker.py`

**Bug:** `ingest_and_update()` caught all exceptions to set the paper status to `"failed"`, then re-raised. But the actual exception was never logged, making it impossible to debug ingestion failures.

**Fix:** Added `logger.exception("Ingestion failed for paper %s (file: %s)", paper_id, file_path)` before setting the status and re-raising.

---

### 32. No Error Handling on DB Insert — `backend/db_papers.py`

**Bug:** `insert_paper()` had no error handling. Constraint violations (e.g., duplicate primary key) or other database errors would propagate as unlogged, uncontrolled exceptions.

**Fix:** Added `try/except` with specific handling for `sqlite3.IntegrityError` (logged as warning) and general exceptions (logged with `logger.exception()`). Both re-raise after logging.

---

### 33. Stale Closure in Message History — `frontend/src/components/InputBar.tsx`

**Bug:** `const history = [...messages, userMsg].map(...)` captured `messages` from the React render closure. If two sends happened in rapid succession, the second send's `messages` wouldn't include the first assistant response yet, resulting in incomplete chat history sent to the server.

**Fix:** Replaced `messages` (from the closure) with `useAppStore.getState().messages`, which reads the current Zustand state at call time rather than the stale render-time snapshot.

---

### 34. Chunk ID Collisions — `frontend/src/components/InputBar.tsx`

**Bug:** Fallback chunk IDs used `chunk_${i}` (array index). Multiple API responses would produce identical IDs (`chunk_0`, `chunk_1`, etc.), causing React key collisions and rendering bugs.

**Fix:** (Fixed as part of Critical #7) Changed to `chunk_${crypto.randomUUID()}_${i}`, ensuring globally unique fallback IDs.

---

### 35. Unnecessary Effect Reruns — `frontend/src/pages/Verify.tsx`

**Bug:** `useEffect` had `[searchParams, navigate]` as dependencies. React Router's `useSearchParams` returns a new object on every render, causing the effect (and the verification API call) to re-run repeatedly.

**Fix:** Extracted `const token = searchParams.get("token")` outside the effect and changed the dependency array to `[token, navigate]`. Also added a `cancelled` flag for cleanup.

---

### 36. Unhandled JSON Parse on Login Success — `frontend/src/pages/Login.tsx`

**Bug:** `const data = await res.json()` on a successful login response had no error handling. If the server returned a 200 with invalid JSON or a missing `access_token` field, the error message would be confusing.

**Fix:** Changed to `await res.json().catch(() => null)` with a subsequent check: `if (!data?.access_token) throw new Error("Invalid response from server")`.

---

### 37. Silent Polling Failure — `frontend/src/components/LeftSidebar.tsx`

**Bug:** The poll function's network errors were silently ignored — no logging, no user feedback, no retry.

**Fix:** (Fixed as part of Critical #9) The poll function now has a `try/catch` that stops polling on network errors rather than leaving orphaned timeouts.

---

## Low Priority Fixes

### 38. Limited Citation Regex — `rag/output_parser.py`

**Bug:** The citation pattern `\[[^\]]+?,\s*\d{4}\]` required exactly a 4-digit year. Citations like `[Author, 2024a]` (with a year suffix) would not be matched.

**Fix:** Extended the pattern to `\[[^\]]+?,\s*\d{4}[a-z]?\]` to optionally match a single lowercase letter suffix.

---

### 39. Hardcoded CORS Origins — `backend/main.py`

**Bug:** CORS `allow_origins` was hardcoded to `["http://localhost:5173", "http://localhost:8080"]`. Any production deployment would require code changes.

**Fix:** Now reads the `CORS_ORIGINS` environment variable (comma-separated list). Falls back to the localhost defaults if not set.

---

### 40. Hardcoded force_rebuild=False — `backend/ingest_pipeline.py`

**Bug:** `ingest_file()` always passed `force_rebuild=False` to `build_index()`. There was no way to force a rebuild for modified files without editing code.

**Fix:** `ingest_file()` now accepts an optional `force_rebuild` parameter. If not provided, it reads the `INGEST_FORCE_REBUILD` environment variable (`1`, `true`, or `yes` to enable).

---

### 41. User Enumeration via Registration — `backend/routers/auth.py`

**Bug:** The register endpoint returned `"Email already registered."` for existing emails but `"Check your email to verify your account."` for new ones. An attacker could enumerate valid email addresses by observing the different responses.

**Fix:** Both paths now return the same generic message: `"If this email is not already registered, a verification link has been sent."`.

---

### 42. Orphaned Citations Render as Broken Buttons — `frontend/src/components/CitationChip.tsx`

**Bug:** When a citation's `sourceFile` didn't match any active chunk, `matchingChunk` was `undefined`. The component still rendered a clickable `<button>` that did nothing on click — no visual or interactive feedback.

**Fix:** Added an early return when `!matchingChunk` that renders a muted, non-clickable `<span>` with a `title="Source chunk not found"` tooltip, clearly indicating the citation is orphaned.

---

### 43. Missing Upload Loading State — `frontend/src/components/LeftSidebar.tsx`

**Bug:** During file upload, there was no visual feedback. Users could click upload multiple times or think the app was frozen.

**Fix:** Added an `isUploading` state. Set to `true` before the API call, reset in a `finally` block. An "Uploading..." message is shown above the upload zone while active.

---

### 44. Unused `index` Prop — `frontend/src/components/ChunkCard.tsx` + `RightSidebar.tsx`

**Bug:** `ChunkCard` accepted an `index` prop that was never used in the component body — a vestigial parameter from an earlier refactor.

**Fix:** Removed `index` from the `ChunkCardProps` interface, the component destructuring, and the call site in `RightSidebar.tsx`.

---

### 45. Pervasive `any` Types — `frontend/src/components/LeftSidebar.tsx`

**Bug:** API responses were typed as `any` throughout `LeftSidebar`, bypassing TypeScript's type checking. If the API schema changed (e.g., `source_file` renamed to `sourceFile`), the error would only appear at runtime.

**Fix:** Introduced a `PaperResponse` interface with proper typed fields (`id`, `source_file`, `status`, etc.). All `.forEach()` callbacks now use this type instead of `any`.

---

### 46. URL Length Risk in Verification — `frontend/src/pages/Verify.tsx`

**Bug:** The verification token was concatenated into the URL with template literals: `` `${apiUrl}/auth/verify?token=${encodeURIComponent(token)}` ``. While `encodeURIComponent` handles encoding, very long JWT tokens could exceed URL length limits on some servers.

**Fix:** Changed to use the `URL` API: `const url = new URL(...); url.searchParams.set("token", token)`, which is the standard-compliant way to construct URLs with query parameters.

---

## Files Modified

| File | Bugs Fixed |
|------|-----------|
| `backend/config.py` | #1 |
| `backend/auth_utils.py` | #2 |
| `backend/main.py` | #39 |
| `backend/db.py` | #15, #25 |
| `backend/db_papers.py` | #32 |
| `backend/deps.py` | #14, #26 |
| `backend/email_utils.py` | #16 |
| `backend/ingest_pipeline.py` | #40 |
| `backend/ingest_worker.py` | #5, #31 |
| `backend/routers/auth.py` | #11, #15, #41 |
| `backend/routers/papers.py` | #12, #13, #19, #29 |
| `backend/routers/chat.py` | #24 |
| `rag/tools.py` | #3 |
| `rag/bm25_index.py` | #4 |
| `rag/ingest.py` | #17, #27, #28 |
| `rag/retriever.py` | #18, #30 |
| `rag/output_parser.py` | #38 |
| `frontend/src/hooks/use-toast.ts` | #6 |
| `frontend/src/components/InputBar.tsx` | #7, #8, #33, #34 |
| `frontend/src/components/LeftSidebar.tsx` | #9, #22, #23, #43, #45 |
| `frontend/src/components/CitationChip.tsx` | #42 |
| `frontend/src/components/ChunkCard.tsx` | #44 |
| `frontend/src/components/RightSidebar.tsx` | #44 |
| `frontend/src/store/useAppStore.ts` | #20, #21 |
| `frontend/src/pages/Index.tsx` | #10 |
| `frontend/src/pages/Verify.tsx` | #35, #46 |
| `frontend/src/pages/Login.tsx` | #36 |
