# retriever.py
from __future__ import annotations

import os
import threading
from typing import Dict, Iterable, List, Tuple, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from rag.bm25_index import bm25_search
from rag.reranker import rerank_documents


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(_PROJECT_ROOT, "chroma_db")

# Retrieval settings
K_BM25 = 20
K_VECTOR = 20
FETCH_K_VECTOR = 40
MMR_LAMBDA = 0.5
RRF_K = 60
MERGED_K = 40

_vs_lock = threading.Lock()
_cached_vectorstore: Optional[Chroma] = None


def _load_vectorstore() -> Chroma:
    global _cached_vectorstore
    with _vs_lock:
        if _cached_vectorstore is not None:
            return _cached_vectorstore
    embedding_fn = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_fn,
    )
    with _vs_lock:
        _cached_vectorstore = store
    return store


def invalidate_vectorstore_cache() -> None:
    global _cached_vectorstore
    with _vs_lock:
        _cached_vectorstore = None


def _doc_key(doc: Document) -> tuple[str, str, str]:
    source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
    paper_id = doc.metadata.get("paper_id") or "noid"
    return (doc.page_content, str(source), str(paper_id))


def _rrf_merge(
    lists: Iterable[List[Document]],
    rrf_k: int = RRF_K,
) -> Tuple[List[Document], Dict[tuple[str, str, str], float]]:
    scores: Dict[tuple[str, str, str], float] = {}
    doc_map: Dict[tuple[str, str, str], Document] = {}

    for docs in lists:
        for rank, doc in enumerate(docs, start=1):
            key = _doc_key(doc)
            doc_map[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank + rrf_k)

    ranked_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    merged_docs = [doc_map[k] for k in ranked_keys]
    return merged_docs, scores


def _build_where(user_id: Optional[str], paper_ids: Optional[list[str]]):
    filters = []
    if user_id:
        filters.append({"user_id": str(user_id)})
    if paper_ids:
        filters.append({"paper_id": {"$in": [str(pid) for pid in paper_ids]}})

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def _retrieve_vector(vectorstore: Chroma, query: str, where):
    return vectorstore.max_marginal_relevance_search(
        query,
        k=K_VECTOR,
        fetch_k=FETCH_K_VECTOR,
        lambda_mult=MMR_LAMBDA,
        filter=where,
    )


def hybrid_retrieve(
    query: str,
    user_id: Optional[str] = None,
    paper_ids: Optional[list[str]] = None,
) -> Tuple[List[Document], Dict[tuple[str, str, str], dict]]:
    if not os.path.isdir(CHROMA_DIR):
        raise FileNotFoundError("Chroma DB not found. Run ingestion first.")

    vectorstore = _load_vectorstore()
    where = _build_where(user_id, paper_ids)

    bm25_docs = bm25_search(query, k=K_BM25, user_id=user_id, paper_ids=paper_ids)
    vector_docs = _retrieve_vector(vectorstore, query, where)

    bm25_rank = {_doc_key(doc): i + 1 for i, doc in enumerate(bm25_docs)}
    vector_rank = {_doc_key(doc): i + 1 for i, doc in enumerate(vector_docs)}

    merged_docs, rrf_scores = _rrf_merge([bm25_docs, vector_docs], rrf_k=RRF_K)
    merged_docs = merged_docs[:MERGED_K]

    reranked_docs, rerank_scores, _backend = rerank_documents(
        query=query,
        docs=merged_docs,
        top_n=20,
        score_threshold=0.0,
    )

    meta_map: Dict[tuple[str, str, str], dict] = {}
    for doc in merged_docs:
        key = _doc_key(doc)
        meta_map[key] = {
            "bm25_rank": bm25_rank.get(key, 0),
            "vector_rank": vector_rank.get(key, 0),
            "rrf_score": float(rrf_scores.get(key, 0.0)),
            "rerank_score": 0.0,
        }

    for idx, score in rerank_scores.items():
        if 0 <= idx < len(merged_docs):
            key = _doc_key(merged_docs[idx])
            meta_map[key]["rerank_score"] = float(score)

    if reranked_docs:
        return reranked_docs, meta_map

    return merged_docs, meta_map
