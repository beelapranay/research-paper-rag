# retriever.py
from __future__ import annotations

import logging
import os
from typing import Dict, Iterable, List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from rag.bm25_index import bm25_search
from rag.reranker import rerank_documents

logger = logging.getLogger(__name__)


CHROMA_DIR = "./chroma_db"

# Retrieval settings
K_BM25 = 20
K_VECTOR = 20
FETCH_K_VECTOR = 40
MMR_LAMBDA = 0.5
RRF_K = 60
MERGED_K = 40


def _load_vectorstore() -> Chroma:
    embedding_fn = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_fn,
    )


def _doc_key(doc: Document) -> tuple[str, str]:
    source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
    return (doc.page_content, str(source))


def _rrf_merge(
    lists: Iterable[List[Document]],
    rrf_k: int = RRF_K,
) -> Tuple[List[Document], Dict[tuple[str, str], float]]:
    scores: Dict[tuple[str, str], float] = {}
    doc_map: Dict[tuple[str, str], Document] = {}

    for docs in lists:
        for rank, doc in enumerate(docs, start=1):
            key = _doc_key(doc)
            doc_map[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank + rrf_k)

    ranked_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    merged_docs = [doc_map[k] for k in ranked_keys]
    return merged_docs, scores


def hybrid_retrieve(query: str) -> Tuple[List[Document], Dict[tuple[str, str], float]]:
    if not os.path.isdir(CHROMA_DIR):
        raise FileNotFoundError("Chroma DB not found. Run ingestion first.")

    try:
        vectorstore = _load_vectorstore()
    except Exception as exc:
        logger.exception("Failed to load Chroma vectorstore")
        raise RuntimeError(f"Vectorstore is corrupted or unreadable: {exc}") from exc
    bm25_docs = bm25_search(query, k=K_BM25)
    vector_docs = vectorstore.max_marginal_relevance_search(
        query,
        k=K_VECTOR,
        fetch_k=FETCH_K_VECTOR,
        lambda_mult=MMR_LAMBDA,
    )

    merged_docs, rrf_scores = _rrf_merge([bm25_docs, vector_docs], rrf_k=RRF_K)
    merged_docs = merged_docs[:MERGED_K]

    reranked_docs, rerank_scores, _backend = rerank_documents(
        query=query,
        docs=merged_docs,
        top_n=5,
        score_threshold=0.3,
    )

    if reranked_docs:
        score_map: Dict[tuple[str, str], float] = {}
        for idx, score in rerank_scores.items():
            key = _doc_key(merged_docs[idx])
            score_map[key] = score
        return reranked_docs, score_map

    return merged_docs, rrf_scores
