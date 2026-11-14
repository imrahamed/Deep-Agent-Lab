import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel


class Brief(BaseModel):
    id: str
    thread_id: str
    title: str
    markdown: str
    created_at: str


class BriefStore:
    def __init__(self, state_dir: Path):
        self.path = state_dir / "briefs.sqlite"
        with self.connect() as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS briefs (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def connect(self):
        from contextlib import closing

        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        return closing(conn)

    def save(self, thread_id: str, title: str, markdown: str) -> str:
        canonical = json.dumps([thread_id, title, markdown], ensure_ascii=False)
        brief_id = sha256(canonical.encode()).hexdigest()[:32]
        with self.connect() as conn, conn:
            conn.execute(
                "INSERT OR IGNORE INTO briefs (id, thread_id, title, markdown) VALUES (?,?,?,?)",
                (brief_id, thread_id, title, markdown),
            )
        return brief_id

    def get(self, brief_id: str) -> Brief | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,)).fetchone()
        return Brief.model_validate(dict(row)) if row else None
