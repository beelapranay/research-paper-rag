import logging
import os
import shutil
import uuid

from backend.db import get_conn
from backend.ingest_pipeline import ingest_file

logger = logging.getLogger(__name__)

UPLOAD_DIR = "backend/uploads"


def ensure_upload_dir() -> None:
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploads(files):
    ensure_upload_dir()
    saved_paths = []
    for file in files:
        filename = file.filename
        file_id = str(uuid.uuid4())
        safe_name = f"{file_id}_{filename}"
        path = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_paths.append(path)
        except Exception:
            logger.exception("Failed to save uploaded file %s", filename)
            raise
        finally:
            file.file.close()
    return saved_paths


def update_paper_status(paper_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE papers SET status = ? WHERE id = ?", (status, paper_id))
        conn.commit()


def ingest_and_update(paper_id: str, file_path: str, user_id: str) -> None:
    try:
        ingest_file(file_path, user_id)
        update_paper_status(paper_id, "indexed")
    except Exception:
        logger.exception("Ingestion failed for paper %s (file: %s)", paper_id, file_path)
        update_paper_status(paper_id, "failed")
        raise
