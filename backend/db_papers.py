from datetime import datetime
import sqlite3
from typing import Optional

from backend.db import get_conn


def init_papers_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                source_file TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


def insert_paper(
    paper_id: str,
    user_id: str,
    title: str,
    authors: str,
    year: int,
    source_file: str,
    status: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (id, user_id, title, authors, year, source_file, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (paper_id, user_id, title, authors, year, source_file, status, datetime.utcnow().isoformat()),
        )
        conn.commit()
