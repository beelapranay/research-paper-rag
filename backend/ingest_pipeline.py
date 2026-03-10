import os

from rag.ingest import build_index, extract_pdf_metadata


def ingest_file(path: str, user_id: str, force_rebuild: bool | None = None) -> None:
    if force_rebuild is None:
        force_rebuild = os.environ.get("INGEST_FORCE_REBUILD", "").lower() in ("1", "true", "yes")
    build_index(file_paths=[path], force_rebuild=force_rebuild, user_id=user_id)


def get_metadata(path: str) -> dict[str, str]:
    return extract_pdf_metadata(path)
