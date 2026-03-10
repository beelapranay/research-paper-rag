# bm25_index.py
import os
import pickle
from typing import Iterable, List

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rank_bm25 import BM25Okapi


CHROMA_DIR = "./chroma_db"
BM25_INDEX_PATH = "./bm25.pkl"
BM25_CHUNKS_PATH = "./bm25_chunks.pkl"


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


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
    if not os.path.isfile(BM25_INDEX_PATH) or not os.path.isfile(BM25_CHUNKS_PATH):
        build_bm25_index(force_rebuild=False)

    try:
        with open(BM25_INDEX_PATH, "rb") as f:
            bm25 = pickle.load(f)
        with open(BM25_CHUNKS_PATH, "rb") as f:
            chunks = pickle.load(f)
    except (pickle.UnpicklingError, EOFError, ValueError, OSError) as exc:
        raise RuntimeError(
            f"BM25 index files are corrupted or unreadable: {exc}. "
            "Delete bm25.pkl / bm25_chunks.pkl and re-run ingestion."
        ) from exc

    return bm25, chunks


def bm25_search(query: str, k: int = 20) -> list[Document]:
    bm25, chunks = _load_bm25()
    if not chunks:
        return []

    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    top_indices = ranked[:k]
    return [chunks[i] for i in top_indices]


if __name__ == "__main__":
    build_bm25_index(force_rebuild=True)
