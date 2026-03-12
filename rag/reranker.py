# reranker.py
from __future__ import annotations

import os
from typing import Dict, List, Tuple

from langchain_core.documents import Document


COHERE_MODEL = "rerank-english-v3.0"
LOCAL_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_cross_encoder = None


def _rerank_with_cohere(query: str, docs: List[Document], top_n: int) -> Tuple[List[Document], List[int], Dict[int, float]]:
    import cohere  # lazy import

    client = cohere.Client(os.environ["COHERE_API_KEY"])
    texts = [doc.page_content for doc in docs]
    resp = client.rerank(
        model=COHERE_MODEL,
        query=query,
        documents=texts,
        top_n=min(top_n, len(texts)),
    )

    ranked_docs: List[Document] = []
    ranked_indices: List[int] = []
    score_map: Dict[int, float] = {}
    for item in resp.results:
        ranked_docs.append(docs[item.index])
        ranked_indices.append(item.index)
        score_map[item.index] = float(item.relevance_score)

    return ranked_docs, ranked_indices, score_map


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(LOCAL_MODEL)
    return _cross_encoder


def _rerank_with_local(query: str, docs: List[Document], top_n: int) -> Tuple[List[Document], List[int], Dict[int, float]]:
    model = _get_cross_encoder()
    pairs = [(query, doc.page_content) for doc in docs]
    scores = model.predict(pairs)

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranked_indices = ranked_indices[: min(top_n, len(ranked_indices))]
    ranked_docs = [docs[i] for i in ranked_indices]
    score_map = {i: float(scores[i]) for i in ranked_indices}
    return ranked_docs, ranked_indices, score_map


def rerank_documents(
    query: str,
    docs: List[Document],
    top_n: int = 5,
    score_threshold: float = 0.3,
) -> Tuple[List[Document], Dict[int, float], str]:
    """
    Returns (reranked_docs, score_map, backend).
    score_map uses original doc index -> score.
    """
    if not docs:
        return [], {}, "none"

    if os.environ.get("COHERE_API_KEY"):
        ranked_docs, ranked_indices, score_map = _rerank_with_cohere(query, docs, top_n)
        backend = "cohere"
    else:
        ranked_docs, ranked_indices, score_map = _rerank_with_local(query, docs, top_n)
        backend = "local"

    filtered_docs: List[Document] = []
    filtered_scores: Dict[int, float] = {}
    for idx in ranked_indices:
        score = score_map.get(idx, 0.0)
        if score >= score_threshold:
            filtered_docs.append(docs[idx])
            filtered_scores[idx] = score

    return filtered_docs, filtered_scores, backend
