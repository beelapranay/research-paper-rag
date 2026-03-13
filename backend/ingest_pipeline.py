from rag.ingest import build_index, extract_pdf_metadata


def ingest_file(path: str, user_id: str, paper_id: str) -> None:
    build_index(file_paths=[path], force_rebuild=False, user_id=user_id, paper_id=paper_id)


def get_metadata(path: str) -> dict[str, str]:
    return extract_pdf_metadata(path)
