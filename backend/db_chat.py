import json
from datetime import datetime
from typing import Optional

from backend.db import get_conn


def init_chat_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                chunks TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


def save_message(
    msg_id: str,
    user_id: str,
    role: str,
    content: str,
    chunks: Optional[list] = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chat_messages (id, user_id, role, content, chunks, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                msg_id,
                user_id,
                role,
                content,
                json.dumps(chunks) if chunks else None,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def get_history(user_id: str) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id, role, content, chunks FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,),
        )
        rows = cur.fetchall()

    messages = []
    for row in rows:
        msg = {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
        }
        if row["chunks"]:
            msg["chunks"] = json.loads(row["chunks"])
        messages.append(msg)
    return messages


def clear_history(user_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        conn.commit()
