import os
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks, HTTPException

from backend import db
from backend.db_papers import init_papers_table, insert_paper
from backend.deps import get_current_user
from backend.ingest_worker import save_uploads, ingest_and_update
from backend.ingest_pipeline import get_metadata

router = APIRouter()

init_papers_table()


@router.get("")
def list_papers(current_user=Depends(get_current_user)):
    with db.get_conn() as conn:
        cur = conn.execute(
            "SELECT id, title, authors, year, source_file, status FROM papers WHERE user_id = ?",
            (current_user["id"],),
        )
        rows = cur.fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "authors": row["authors"],
            "year": row["year"],
            "source_file": row["source_file"],
            "status": row["status"],
        }
        for row in rows
    ]


@router.post("/upload")
def upload_papers(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user=Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    saved_paths = save_uploads(files)
    results = []

    for path, file in zip(saved_paths, files):
        paper_id = str(uuid.uuid4())
        meta = get_metadata(path)

        title = meta.get("title") or os.path.splitext(file.filename)[0]
        authors = meta.get("authors") or "Unknown"
        year_str = meta.get("year") or "0"
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            year = 0

        insert_paper(
            paper_id=paper_id,
            user_id=current_user["id"],
            title=title,
            authors=authors,
            year=year,
            source_file=file.filename,
            status="indexing",
        )

        background_tasks.add_task(ingest_and_update, paper_id, path, current_user["id"])

        results.append({"id": paper_id, "source_file": file.filename, "status": "indexing"})

    return results


@router.post("/{paper_id}/reindex")
def reindex_paper(
    paper_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Delete stale chunks from ChromaDB and re-ingest the paper."""
    with db.get_conn() as conn:
        cur = conn.execute(
            "SELECT id, source_file FROM papers WHERE id = ? AND user_id = ?",
            (paper_id, current_user["id"]),
        )
        paper = cur.fetchone()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    # Remove old chunks from ChromaDB
    _remove_chunks_for_paper(paper_id)

    # Find the uploaded file
    upload_dir = "backend/uploads"
    upload_path = None
    if os.path.isdir(upload_dir):
        for name in os.listdir(upload_dir):
            if name.endswith(paper["source_file"]):
                upload_path = os.path.join(upload_dir, name)
                break

    if not upload_path or not os.path.isfile(upload_path):
        raise HTTPException(status_code=404, detail="Upload file not found on disk. Please re-upload.")

    # Update status and re-ingest
    with db.get_conn() as conn:
        conn.execute("UPDATE papers SET status = 'indexing' WHERE id = ?", (paper_id,))
        conn.commit()

    background_tasks.add_task(ingest_and_update, paper_id, upload_path, current_user["id"])
    return {"id": paper_id, "status": "indexing"}


def _remove_chunks_for_paper(paper_id: str) -> None:
    """Remove all chunks for a given paper_id from ChromaDB and invalidate caches."""
    from rag.retriever import _load_vectorstore, invalidate_vectorstore_cache, CHROMA_DIR
    from rag.bm25_index import invalidate_bm25_cache, build_bm25_index

    if not os.path.isdir(CHROMA_DIR):
        return

    store = _load_vectorstore()
    results = store.get(where={"paper_id": str(paper_id)})
    ids = results.get("ids", []) if isinstance(results, dict) else []
    if ids:
        store._collection.delete(ids=ids)

    invalidate_vectorstore_cache()
    invalidate_bm25_cache()
    build_bm25_index(force_rebuild=True)


@router.delete("/{paper_id}")
def delete_paper(paper_id: str, current_user=Depends(get_current_user)):
    # Clean up ChromaDB chunks first
    _remove_chunks_for_paper(paper_id)

    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM papers WHERE id = ? AND user_id = ?",
            (paper_id, current_user["id"]),
        )
        conn.commit()
    return {"deleted": True}
