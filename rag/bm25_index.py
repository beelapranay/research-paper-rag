# bm25_index.py
import os
import pickle
import re
import threading
from typing import List, Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rank_bm25 import BM25Okapi


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(_PROJECT_ROOT, "chroma_db")
BM25_INDEX_PATH = os.path.join(_PROJECT_ROOT, "bm25.pkl")
BM25_CHUNKS_PATH = os.path.join(_PROJECT_ROOT, "bm25_chunks.pkl")

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "were", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "this", "that", "these", "those", "not", "no", "nor", "so", "if",
    "then", "than", "too", "very", "just", "about", "above", "after",
    "again", "all", "also", "am", "any", "because", "before", "between",
    "both", "each", "few", "more", "most", "other", "our", "out", "own",
    "same", "some", "such", "up", "only", "into", "over", "under", "which",
    "while", "who", "whom", "what", "when", "where", "why", "how",
})

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

# In-memory cache
_cache_lock = threading.Lock()
_cached_bm25: Optional[BM25Okapi] = None
_cached_chunks: Optional[List[Document]] = None


def _tokenize(text: str) -> list[str]:
    text = _PUNCT_RE.sub(" ", text.lower())
    return [tok for tok in text.split() if tok not in STOPWORDS and len(tok) > 1]


def _load_all_chunks() -> list[Document]:
    if not os.path.isdir(CHROMA_DIR):
        raise FileNotFoundError("Chroma DB not found. Run ingestion first.")

    store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001"),
    )
    rows = store.get(include=["documents", "metadatas"])
    docs = rows.get("documents", []) if isinstance(rows, dict) else []
    metas = rows.get("metadatas", []) if isinstance(rows, dict) else []

    chunks: list[Document] = []
    for text, meta in zip(docs, metas):
        if not text:
            continue
        chunks.append(Document(page_content=text, metadata=meta or {}))
    return chunks


def build_bm25_index(force_rebuild: bool = False) -> None:
    load_dotenv()

    if not force_rebuild and os.path.isfile(BM25_INDEX_PATH) and os.path.isfile(BM25_CHUNKS_PATH):
        print("BM25 index already exists. Pass force_rebuild=True to rebuild.")
        return

    chunks = _load_all_chunks()
    if not chunks:
        print("No chunks found in Chroma DB.")
        return

    tokenized_corpus = [_tokenize(doc.page_content) for doc in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25, f)
    with open(BM25_CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    print(f"BM25 index built for {len(chunks)} chunks.")


def _load_bm25() -> tuple[BM25Okapi, list[Document]]:
    global _cached_bm25, _cached_chunks

    with _cache_lock:
        if _cached_bm25 is not None and _cached_chunks is not None:
            return _cached_bm25, _cached_chunks

    if not os.path.isfile(BM25_INDEX_PATH) or not os.path.isfile(BM25_CHUNKS_PATH):
        build_bm25_index(force_rebuild=True)

    with open(BM25_INDEX_PATH, "rb") as f:
        bm25 = pickle.load(f)
    with open(BM25_CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)

    with _cache_lock:
        _cached_bm25 = bm25
        _cached_chunks = chunks

    return bm25, chunks


def invalidate_bm25_cache() -> None:
    global _cached_bm25, _cached_chunks
    with _cache_lock:
        _cached_bm25 = None
        _cached_chunks = None
    for path in (BM25_INDEX_PATH, BM25_CHUNKS_PATH):
        if os.path.isfile(path):
            os.remove(path)


def _match_doc(doc: Document, user_id: Optional[str], paper_ids: Optional[list[str]]) -> bool:
    if user_id and str(doc.metadata.get("user_id")) != str(user_id):
        return False
    if paper_ids:
        return str(doc.metadata.get("paper_id")) in set(map(str, paper_ids))
    return True


def bm25_search(query: str, k: int = 20, user_id: Optional[str] = None, paper_ids: Optional[list[str]] = None) -> list[Document]:
    bm25, chunks = _load_bm25()
    if not chunks:
        return []

    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results: list[Document] = []
    for idx in ranked:
        doc = chunks[idx]
        if _match_doc(doc, user_id, paper_ids):
            results.append(doc)
        if len(results) >= k:
            break

    return results


if __name__ == "__main__":
    build_bm25_index(force_rebuild=True)
