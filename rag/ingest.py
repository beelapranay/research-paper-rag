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

from rag.bm25_index import invalidate_bm25_cache, build_bm25_index
from rag.retriever import invalidate_vectorstore_cache


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(_PROJECT_ROOT, "chroma_db")
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300


def _clean_text(text: str) -> str:
    """Normalize whitespace, fix ligatures, remove non-printables, and fix missing spaces."""
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

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Insert space between a lowercase letter and an uppercase letter (camelCase joins
    # from PDF extraction, e.g. "rewardstates" won't match but "rewardStates" will).
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Insert space between a letter/closing-paren and an opening paren: "word(x)" -> "word (x)"
    text = re.sub(r"([a-zA-Z)])(\()", r"\1 \2", text)
    # Insert space between a closing paren and a letter: "(x)word" -> "(x) word"
    text = re.sub(r"(\))([a-zA-Z])", r"\1 \2", text)
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
        source = doc.metadata.get("source_path") or doc.metadata.get("source_file") or "unknown"
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


def _looks_like_author_line(line: str) -> bool:
    if len(line) < 3 or len(line) > 300:
        return False
    skip_starts = ("abstract", "introduction", "keywords", "doi", "http", "arxiv", "©")
    if line.lower().startswith(skip_starts):
        return False
    # Heuristic: author lines typically contain commas or "and", with mostly
    # capitalized words and few digits (unlike titles which are longer phrases).
    has_separator = "," in line or " and " in line.lower()
    digit_ratio = sum(c.isdigit() for c in line) / max(len(line), 1)
    cap_words = sum(1 for w in line.split() if w[0:1].isupper())
    if has_separator and digit_ratio < 0.15 and cap_words >= 2:
        return True
    return False


def _extract_doc_metadata(first_page_text: str, filename: str) -> dict[str, str]:
    lines = [ln.strip() for ln in first_page_text.splitlines() if ln.strip()]
    title = ""
    authors = ""
    year = ""

    title_idx = -1
    for i, line in enumerate(lines):
        if 10 <= len(line) <= 200 and not line.lower().startswith("abstract"):
            title = line
            title_idx = i
            break

    # Look for author-like lines immediately after the title
    if title_idx >= 0:
        for line in lines[title_idx + 1 : title_idx + 5]:
            if line.lower().startswith("abstract"):
                break
            if _looks_like_author_line(line):
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


def extract_pdf_metadata(file_path: str) -> dict[str, str]:
    loader = PDFPlumberLoader(file_path)
    docs = loader.load()
    if not docs:
        base = os.path.splitext(os.path.basename(file_path))[0]
        return {
            "title": base,
            "authors": "Unknown",
            "year": "Unknown",
        }
    return _extract_doc_metadata(docs[0].page_content or "", file_path)


def build_index(
    file_paths: list[str] | None = None,
    force_rebuild: bool = False,
    user_id: str | None = None,
    paper_id: str | None = None,
) -> None:
    load_dotenv()

    if file_paths is None:
        file_paths = [DATA_DIR]

    pdf_files = _collect_pdf_files(file_paths)
    if not pdf_files:
        print("No PDF files found. Add PDFs to ./data or pass file paths.")
        return

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
            existing_sources = set()
            for m in metadatas:
                if not isinstance(m, dict):
                    continue
                src = m.get("source_path") or m.get("source_file") or m.get("source")
                uid = m.get("user_id") or ""
                if src:
                    existing_sources.add((os.path.abspath(src), str(uid)))

            pdf_files = [
                path for path in pdf_files
                if (os.path.abspath(path), str(user_id or "")) not in existing_sources
            ]
            if not pdf_files:
                print("All PDFs are already indexed. Pass force_rebuild=True to re-index.")
                return

    docs = []
    for path in pdf_files:
        loader = PDFPlumberLoader(path)
        file_docs = loader.load()
        # Strip UUID prefix added by save_uploads (e.g. "ab12cd34_paper.pdf" -> "paper.pdf")
        raw_name = os.path.basename(path)
        filename = re.sub(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_", "", raw_name)
        for doc in file_docs:
            doc.metadata["source_file"] = filename
            doc.metadata["source_path"] = os.path.abspath(path)
            doc.metadata["source"] = filename
            if user_id:
                doc.metadata["user_id"] = user_id
            if paper_id:
                doc.metadata["paper_id"] = paper_id
        docs.extend(file_docs)

    _strip_headers_footers(docs)
    for doc in docs:
        doc.page_content = _clean_text(doc.page_content)

    docs = [doc for doc in docs if len(doc.page_content) > 100]

    if not docs:
        print("No content found after cleaning. Check your PDFs.")
        return

    first_page_by_source: dict[str, str] = {}
    for doc in docs:
        source = doc.metadata.get("source_path") or doc.metadata.get("source_file") or "unknown"
        if source not in first_page_by_source:
            first_page_by_source[source] = doc.page_content

    meta_by_source = {
        source: _extract_doc_metadata(text, source)
        for source, text in first_page_by_source.items()
    }

    for doc in docs:
        source = doc.metadata.get("source_path") or doc.metadata.get("source_file") or "unknown"
        doc.metadata.update(meta_by_source.get(source, {}))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    splits = text_splitter.split_documents(docs)

    for i, split in enumerate(splits):
        split.metadata["chunk_index"] = i
        source = split.metadata.get("source_file") or split.metadata.get("source") or "unknown"
        # Use short paper_id prefix (first 8 chars) for readability
        pid = split.metadata.get("paper_id") or "noid"
        short_pid = pid[:8] if len(pid) > 8 else pid
        split.metadata["chunk_id"] = f"{short_pid}:{source}:{i}"

    print(f"Split into {len(splits)} chunks from {len(docs)} document(s).")

    embedding = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    if os.path.isdir(CHROMA_DIR) and not force_rebuild:
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embedding,
        )
        vectorstore.add_documents(splits)
    else:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embedding,
            persist_directory=CHROMA_DIR,
        )

    # Invalidate caches and rebuild BM25 eagerly so queries immediately see new data
    invalidate_bm25_cache()
    invalidate_vectorstore_cache()
    build_bm25_index(force_rebuild=True)

    print(f"Indexing complete! {vectorstore._collection.count()} chunks stored.")
