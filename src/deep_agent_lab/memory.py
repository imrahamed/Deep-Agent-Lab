"""Persistent, scoped preferences; policy evidence remains in the versioned corpus."""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from deep_agent_lab.security import Principal


class MemoryRecord(BaseModel):
    id: str
    tenant: str
    scope: Literal["user", "team", "project"] = "user"
    subject: str
    content: str = Field(min_length=1)
    source_type: Literal["user_preference", "reviewed_note", "approved_policy"]
    source_id: str
    source_revision: str | None = None
    created_at: float = Field(default_factory=time.time)
    expires_at: float | None = None
    status: Literal["active", "superseded", "deleted"] = "active"
    supersedes_id: str | None = None
    version: int = Field(default=1, ge=1)


def check_scope(principal: Principal, tenant: str, scope: str, subject: str):
    subjects = {"user": {principal.user}, "team": principal.teams, "project": principal.projects}
    if (
        tenant != principal.tenant
        or "memory" not in principal.permissions
        or subject not in subjects.get(scope, set())
    ):
        raise PermissionError("Memory scope is not authorized")


class MemoryStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, body TEXT)")
            # Namespace physical keys while retaining the logical ID in the record body.
            for key, body in db.execute("SELECT id,body FROM memories").fetchall():
                record = MemoryRecord.model_validate_json(body)
                scoped_key = self.key(record.tenant, record.scope, record.subject, record.id)
                if key != scoped_key:
                    db.execute("INSERT OR IGNORE INTO memories VALUES (?,?)", (scoped_key, body))
                    db.execute("DELETE FROM memories WHERE id=?", (key,))

    @staticmethod
    def key(tenant, scope, subject, record_id):
        return hashlib.sha256(json.dumps([tenant, scope, subject, record_id]).encode()).hexdigest()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, principal: Principal, record: MemoryRecord, *, reviewed: bool = False):
        check_scope(principal, record.tenant, record.scope, record.subject)
        if record.source_type != "user_preference" and not reviewed:
            raise PermissionError("Policy and note memory requires explicit trusted review")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if record.supersedes_id:
                old_key = self.key(
                    record.tenant, record.scope, record.subject, record.supersedes_id
                )
                row = db.execute("SELECT body FROM memories WHERE id=?", (old_key,)).fetchone()
                if not row:
                    raise ValueError("Correction target does not exist")
                old = MemoryRecord.model_validate_json(row[0])
                if (
                    (old.tenant, old.scope, old.subject)
                    != (record.tenant, record.scope, record.subject)
                    or record.version != old.version + 1
                    or old.status != "active"
                ):
                    raise ValueError("Correction scope/version conflict")
                old.status = "superseded"
                db.execute(
                    "UPDATE memories SET body=? WHERE id=?", (old.model_dump_json(), old_key)
                )
            db.execute(
                "INSERT INTO memories VALUES (?,?)",
                (
                    self.key(record.tenant, record.scope, record.subject, record.id),
                    record.model_dump_json(),
                ),
            )

    def visible(self, principal: Principal, scope="user", subject=None, *, now=None):
        subject = principal.user if subject is None else subject
        check_scope(principal, principal.tenant, scope, subject)
        now = time.time() if now is None else now
        with self.connect() as db:
            records = [
                MemoryRecord.model_validate(json.loads(row[0]))
                for row in db.execute("SELECT body FROM memories ORDER BY id")
            ]
        return [
            r
            for r in records
            if (r.tenant, r.scope, r.subject) == (principal.tenant, scope, subject)
            and r.status == "active"
            and (r.expires_at is None or r.expires_at > now)
        ]

    def delete(self, principal: Principal, record_id: str, *, scope="user", subject=None):
        subject = principal.user if subject is None else subject
        check_scope(principal, principal.tenant, scope, subject)
        key = self.key(principal.tenant, scope, subject, record_id)
        with self.connect() as db:
            row = db.execute("SELECT body FROM memories WHERE id=?", (key,)).fetchone()
            if not row:
                return
            record = MemoryRecord.model_validate_json(row[0])
            check_scope(principal, record.tenant, record.scope, record.subject)
            db.execute("DELETE FROM memories WHERE id=?", (key,))
