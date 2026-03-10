import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from backend.config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                verification_token TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def create_user(
    user_id: str,
    full_name: str,
    email: str,
    hashed_password: str,
    verification_token: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (id, full_name, email, hashed_password, is_verified, verification_token, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
            """,
            (user_id, full_name, email, hashed_password, verification_token, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        return cur.fetchone()


def get_user_by_token(token: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE verification_token = ?", (token,))
        return cur.fetchone()


def mark_verified(user_id: str, token: str | None = None) -> bool:
    """Atomically verify user; returns True if a row was actually updated."""
    with get_conn() as conn:
        if token:
            cur = conn.execute(
                "UPDATE users SET is_verified = 1, verification_token = NULL "
                "WHERE id = ? AND verification_token = ?",
                (user_id, token),
            )
        else:
            cur = conn.execute(
                "UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?",
                (user_id,),
            )
        conn.commit()
        return cur.rowcount > 0


def update_verification_token(user_id: str, token: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET verification_token = ? WHERE id = ?",
            (token, user_id),
        )
        conn.commit()
