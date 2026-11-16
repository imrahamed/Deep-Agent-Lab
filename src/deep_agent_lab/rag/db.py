"""PostgreSQL is authoritative. OpenSearch results must resolve to active SQL chunks."""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from deep_agent_lab.settings import Settings
from deep_agent_lab.tracing import Tracing

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS deep_agent_lab;
CREATE TABLE IF NOT EXISTS deep_agent_lab.rag_documents (
    id text PRIMARY KEY,
    title text NOT NULL,
    source text NOT NULL UNIQUE,
    content text NOT NULL,
    revision text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS deep_agent_lab.rag_chunks (
    id text PRIMARY KEY,
    document_id text NOT NULL REFERENCES deep_agent_lab.rag_documents(id) ON DELETE CASCADE,
    position integer NOT NULL,
    content text NOT NULL,
    UNIQUE (document_id, position)
);
CREATE INDEX IF NOT EXISTS rag_chunks_document_idx ON deep_agent_lab.rag_chunks(document_id);
"""


class Database:
    def __init__(self, settings: Settings, tracing: Tracing | None = None):
        self.dsn = settings.postgres_dsn.get_secret_value()
        self.tracing = tracing or Tracing()

    @contextmanager
    def connect(self):
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=10) as connection:
            yield connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended('deep_agent_lab.schema', 0))"
            )
            connection.execute(SCHEMA)

    def health(self) -> dict:
        with self.connect() as connection:
            count = connection.execute(
                "SELECT count(*) AS n FROM deep_agent_lab.rag_documents"
            ).fetchone()["n"]
        return {"status": "ok", "documents": count}

    def documents(self) -> list[dict]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, title, source, revision, updated_at FROM deep_agent_lab.rag_documents "
                "ORDER BY updated_at DESC LIMIT 100"
            ).fetchall()

    def document_ids(self) -> list[str]:
        with self.connect() as connection:
            return [
                row["id"]
                for row in connection.execute("SELECT id FROM deep_agent_lab.rag_documents")
            ]

    def hydrate(self, ids: list[str]) -> dict[str, dict]:
        if not ids:
            return {}
        with self.tracing.span("postgres.hydrate", metadata={"candidate_count": len(ids)}) as span:
            rows = self._hydrate(ids)
            span.update(metadata={"active_count": len(rows)})
            return {row["chunk_id"]: row for row in rows}

    def _hydrate(self, ids: list[str]) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT c.id AS chunk_id, c.document_id, c.position, c.content AS text, "
                "d.title, d.source, d.revision FROM deep_agent_lab.rag_chunks c "
                "JOIN deep_agent_lab.rag_documents d ON d.id=c.document_id "
                "WHERE c.id = ANY(%s)",
                (ids,),
            ).fetchall()
        return rows
