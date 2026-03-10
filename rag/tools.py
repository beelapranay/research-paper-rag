# tools.py
import os
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

from rag.retriever import hybrid_retrieve

load_dotenv()

# Retrieval uses hybrid BM25 + vector with RRF (see retriever.py).


def _build_index_if_needed() -> None:
    from rag.ingest import build_index
    build_index()


def _load_vectorstore() -> Chroma:
    embedding_fn = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    if not os.path.isdir("./chroma_db"):
        _build_index_if_needed()

    store = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embedding_fn,
    )

    if store._collection.count() == 0:
        _build_index_if_needed()
        store = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embedding_fn,
        )

    return store


vectorstore = _load_vectorstore()


def _is_ingestion_question(query: str) -> bool:
    q = query.lower()
    keywords = ["ingest", "indexed", "index", "source", "url", "what did you load"]
    return any(word in q for word in keywords)


def _format_sources() -> str:
    rows = vectorstore.get(include=["metadatas"])
    metadatas = rows.get("metadatas", []) if isinstance(rows, dict) else []

    sources = []
    for metadata in metadatas:
        if isinstance(metadata, dict):
            source = metadata.get("source")
            if source:
                sources.append(source)

    unique_sources = sorted(set(sources))
    if not unique_sources:
        return "No source metadata found in the current vector store."

    return "Ingested sources:\n" + "\n".join(f"- {source}" for source in unique_sources)


@tool
def retrieve_info(query: str):
    """Searches the knowledge base for relevant information."""
    if _is_ingestion_question(query):
        return _format_sources()

    docs, rrf_scores = hybrid_retrieve(query)
    if not docs:
        return []

    formatted_docs = []
    for doc in docs:
        source = "unknown"
        if doc.metadata:
            source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
        key = (doc.page_content, str(source))
        score = rrf_scores.get(key)
        formatted_docs.append({
            "content": doc.page_content,
            "score": float(score) if score is not None else None,
            "source": source,
            "title": doc.metadata.get("title") if doc.metadata else None,
            "authors": doc.metadata.get("authors") if doc.metadata else None,
            "year": doc.metadata.get("year") if doc.metadata else None,
        })

    return formatted_docs
