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
        year = int(year_str) if year_str.isdigit() else 0

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


@router.delete("/{paper_id}")
def delete_paper(paper_id: str, current_user=Depends(get_current_user)):
    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM papers WHERE id = ? AND user_id = ?",
            (paper_id, current_user["id"]),
        )
        conn.commit()
    return {"deleted": True}
