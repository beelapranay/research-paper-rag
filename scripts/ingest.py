# ingest.py
import os
import re
import shutil
from collections import Counter, defaultdict
from typing import Iterable

from dotenv import load_dotenv
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma


CHROMA_DIR = "./chroma_db"
DATA_DIR = "./data"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300


def _clean_text(text: str) -> str:
    """Normalize whitespace, fix ligatures, and remove non-printables."""
    ligatures = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ﬆ": "st",
    }
    for src, dst in ligatures.items():
        text = text.replace(src, dst)

    # Remove zero-width and non-printable characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse runs of whitespace/newlines into a single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _collect_pdf_files(paths: Iterable[str]) -> list[str]:
    pdfs: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            for name in os.listdir(path):
                if name.lower().endswith(".pdf"):
                    pdfs.append(os.path.abspath(os.path.join(path, name)))
        elif path.lower().endswith(".pdf") and os.path.isfile(path):
            pdfs.append(os.path.abspath(path))
    return sorted(set(pdfs))


def _strip_headers_footers(docs: list) -> None:
    """Remove repeated header/footer lines per source_file."""
    grouped: dict[str, list] = defaultdict(list)
    for doc in docs:
        source = doc.metadata.get("source_file", "unknown")
        grouped[source].append(doc)

    for source, pages in grouped.items():
        header_counts: Counter[str] = Counter()
        footer_counts: Counter[str] = Counter()

        page_lines = []
        for doc in pages:
            raw = doc.page_content or ""
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            page_lines.append(lines)
            if lines:
                header_counts[lines[0]] += 1
                footer_counts[lines[-1]] += 1

        if not page_lines:
            continue

        threshold = max(2, int(len(page_lines) * 0.6))
        header_set = {
            line for line, count in header_counts.items()
            if count >= threshold and len(line) < 120
        }
        footer_set = {
            line for line, count in footer_counts.items()
            if count >= threshold and len(line) < 120
        }

        # Always remove pure page-number lines
        for i, lines in enumerate(page_lines):
            filtered = []
            for line in lines:
                lower = line.lower()
                if line in header_set or line in footer_set:
                    continue
                if re.fullmatch(r"\d+", line):
                    continue
                if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", lower):
                    continue
                filtered.append(line)
            pages[i].page_content = "\n".join(filtered)


def _extract_doc_metadata(first_page_text: str, filename: str) -> dict[str, str]:
    lines = [ln.strip() for ln in first_page_text.splitlines() if ln.strip()]
    title = ""
    authors = ""
    year = ""

    for line in lines:
        if 10 <= len(line) <= 200 and not line.lower().startswith("abstract"):
            title = line
            break

    for line in lines[1:5]:
        if "abstract" in line.lower():
            continue
        if any(ch.isalpha() for ch in line) and ("," in line or " and " in line):
            authors = line
            break

    match = re.search(r"(19|20)\d{2}", first_page_text)
    if match:
        year = match.group(0)

    if not title:
        title = os.path.splitext(os.path.basename(filename))[0]
    if not authors:
        authors = "Unknown"
    if not year:
        year = "Unknown"

    return {"title": title, "authors": authors, "year": year}


def build_index(file_paths: list[str] | None = None, force_rebuild: bool = False) -> None:
    load_dotenv()

    if file_paths is None:
        file_paths = [DATA_DIR]

    pdf_files = _collect_pdf_files(file_paths)
    if not pdf_files:
        print("No PDF files found. Add PDFs to ./data or pass file paths.")
        return

    # Wipe existing DB to prevent duplicates on re-ingestion
    if os.path.isdir(CHROMA_DIR):
        if force_rebuild:
            shutil.rmtree(CHROMA_DIR)
            print(f"Cleared existing index at {CHROMA_DIR}")
        else:
            existing = Chroma(
                persist_directory=CHROMA_DIR,
                embedding_function=GoogleGenerativeAIEmbeddings(
                    model="models/gemini-embedding-001"
                ),
            )
            rows = existing.get(include=["metadatas"])
            metadatas = rows.get("metadatas", []) if isinstance(rows, dict) else []
            existing_sources = {
                os.path.abspath(m.get("source_file") or m.get("source"))
                for m in metadatas
                if isinstance(m, dict) and (m.get("source_file") or m.get("source"))
            }
            pdf_files = [
                path for path in pdf_files
                if os.path.abspath(path) not in existing_sources
            ]
            if not pdf_files:
                print("All PDFs are already indexed. Pass force_rebuild=True to re-index.")
                return

    # 1. Load PDFs (one Document per page)
    docs = []
    for path in pdf_files:
        loader = PDFPlumberLoader(path)
        file_docs = loader.load()
        for doc in file_docs:
            doc.metadata["source_file"] = os.path.abspath(path)
            doc.metadata["source"] = os.path.abspath(path)
        docs.extend(file_docs)

    # 2. Remove headers/footers, clean text
    _strip_headers_footers(docs)
    for doc in docs:
        doc.page_content = _clean_text(doc.page_content)

    # Remove docs that are essentially empty after cleaning
    docs = [doc for doc in docs if len(doc.page_content) > 100]

    if not docs:
        print("No content found after cleaning. Check your PDFs.")
        return

    # 3. Attach doc-level metadata (title/authors/year)
    first_page_by_source: dict[str, str] = {}
    for doc in docs:
        source = doc.metadata.get("source_file", "unknown")
        if source not in first_page_by_source:
            first_page_by_source[source] = doc.page_content

    meta_by_source = {
        source: _extract_doc_metadata(text, source)
        for source, text in first_page_by_source.items()
    }

    for doc in docs:
        source = doc.metadata.get("source_file", "unknown")
        doc.metadata.update(meta_by_source.get(source, {}))

    # 4. Split — larger chunks to preserve more context per embedding
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # Prefer paragraph > sentence > word breaks
    )
    splits = text_splitter.split_documents(docs)

    # Attach chunk index to metadata for debugging
    for i, split in enumerate(splits):
        split.metadata["chunk_index"] = i

    print(f"Split into {len(splits)} chunks from {len(docs)} document(s).")

    embedding = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    # 5. Embed and store
    if os.path.isdir(CHROMA_DIR) and not force_rebuild:
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embedding,
        )
        vectorstore.add_documents(splits)
        if hasattr(vectorstore, "persist"):
            vectorstore.persist()
    else:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embedding,
            persist_directory=CHROMA_DIR,
        )

    print(f"Indexing complete! {vectorstore._collection.count()} chunks stored.")


if __name__ == "__main__":
    build_index(force_rebuild=True)
