# tools.py
import os

from dotenv import load_dotenv
from langchain_core.tools import tool

from rag.retriever import hybrid_retrieve, _load_vectorstore, CHROMA_DIR

load_dotenv()


def _ensure_index() -> None:
    if not os.path.isdir(CHROMA_DIR):
        from rag.ingest import build_index
        build_index()
        return

    store = _load_vectorstore()
    if store._collection.count() == 0:
        from rag.ingest import build_index
        build_index()


def _is_ingestion_question(query: str) -> bool:
    q = query.lower()
    keywords = ["ingest", "indexed", "index", "source", "url", "what did you load"]
    return any(word in q for word in keywords)


def _format_sources() -> str:
    store = _load_vectorstore()
    rows = store.get(include=["metadatas"])
    metadatas = rows.get("metadatas", []) if isinstance(rows, dict) else []

    sources = []
    for metadata in metadatas:
        if isinstance(metadata, dict):
            source = metadata.get("source") or metadata.get("source_file")
            if source:
                sources.append(source)

    unique_sources = sorted(set(sources))
    if not unique_sources:
        return "No source metadata found in the current vector store."

    return "Ingested sources:\n" + "\n".join(f"- {source}" for source in unique_sources)


@tool
def retrieve_info(query: str):
    """Searches the research paper knowledge base for relevant information.

    Use this tool to find specific claims, data, methods, or findings from
    ingested research papers. Returns ranked document chunks with relevance
    scores, source file, title, authors, and year metadata.
    """
    _ensure_index()

    if _is_ingestion_question(query):
        return _format_sources()

    docs, meta_map = hybrid_retrieve(query)
    if not docs:
        return []

    formatted_docs = []
    for doc in docs:
        source = "unknown"
        paper_id = "noid"
        if doc.metadata:
            source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
            paper_id = doc.metadata.get("paper_id") or "noid"
        key = (doc.page_content, str(source), str(paper_id))
        meta = meta_map.get(key, {})
        formatted_docs.append({
            "content": doc.page_content,
            "score": meta.get("rerank_score") or meta.get("rrf_score"),
            "source": source,
            "title": doc.metadata.get("title") if doc.metadata else None,
            "authors": doc.metadata.get("authors") if doc.metadata else None,
            "year": doc.metadata.get("year") if doc.metadata else None,
            "chunk_id": doc.metadata.get("chunk_id") if doc.metadata else None,
        })

    return formatted_docs
