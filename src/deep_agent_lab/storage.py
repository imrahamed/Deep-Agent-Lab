import json
import sqlite3
import time
from contextlib import contextmanager
from contextvars import ContextVar
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
        state_dir.mkdir(parents=True, exist_ok=True)
        self.path = state_dir / "briefs.sqlite"
        self._guard = ContextVar(f"brief_guard_{id(self)}", default=None)
        self._trace = ContextVar(f"brief_trace_{id(self)}", default=None)
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_actions (
                    id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, payload TEXT NOT NULL,
                    digest TEXT NOT NULL, revisions TEXT NOT NULL, version INTEGER NOT NULL,
                    status TEXT NOT NULL, expires REAL NOT NULL, brief_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_decisions (
                    action_id TEXT PRIMARY KEY, request TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifact_lineage (
                    brief_id TEXT PRIMARY KEY, action_id TEXT NOT NULL, thread_id TEXT NOT NULL,
                    job_id TEXT, trace_id TEXT, evidence_revisions TEXT NOT NULL,
                    evaluation_version TEXT NOT NULL
                )
            """)

    @property
    def commit_guard(self):
        return self._guard.get()

    @commit_guard.setter
    def commit_guard(self, guard):
        self._guard.set(guard)

    @contextmanager
    def trace_context(self, trace_id):
        token = self._trace.set(trace_id)
        try:
            yield
        finally:
            self._trace.reset(token)

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

    @staticmethod
    def payload(thread_id, title, markdown, revisions):
        return json.dumps(
            {
                "thread_id": thread_id,
                "operation": "save_brief",
                "title": title,
                "markdown": markdown,
                "revisions": revisions,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def propose(self, action_id, thread_id, title, markdown, revisions, *, ttl=3600):
        if ttl <= 0:
            raise ValueError("Review TTL must be positive")
        payload = self.payload(thread_id, title, markdown, revisions)
        digest = sha256(payload.encode()).hexdigest()
        with self.connect() as conn, conn:
            conn.execute(
                "INSERT OR IGNORE INTO review_actions VALUES (?,?,?,?,?,1,'PENDING',?,NULL)",
                (
                    action_id,
                    thread_id,
                    payload,
                    digest,
                    json.dumps(revisions, sort_keys=True),
                    time.time() + ttl,
                ),
            )
            row = conn.execute("SELECT * FROM review_actions WHERE id=?", (action_id,)).fetchone()
            if row["digest"] != digest or row["thread_id"] != thread_id:
                raise ValueError("Proposal identity was reused with different content")
        return dict(row)

    def review(self, action_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM review_actions WHERE id=?", (action_id,)).fetchone()
        return dict(row) if row else None

    def decide(
        self,
        action_id,
        decision,
        current_revisions,
        *,
        expected_digest=None,
        expected_version=None,
        title=None,
        markdown=None,
    ):
        self.decide_many(
            [
                dict(
                    action_id=action_id,
                    decision=decision,
                    current_revisions=current_revisions,
                    expected_digest=expected_digest,
                    expected_version=expected_version,
                    title=title,
                    markdown=markdown,
                )
            ]
        )

    def decide_many(self, actions):
        """Authorize an entire review batch atomically, or leave every action pending."""
        with self.connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            for action in actions:
                self._decide(conn, **action)

    def _decide(
        self,
        conn,
        action_id,
        decision,
        current_revisions,
        *,
        expected_digest=None,
        expected_version=None,
        title=None,
        markdown=None,
    ):
        """Trusted service boundary; an edit explicitly approves its newly validated payload."""
        request = json.dumps(
            {
                "decision": decision,
                "current_revisions": current_revisions,
                "expected_digest": expected_digest,
                "expected_version": expected_version,
                "title": title,
                "markdown": markdown,
            },
            sort_keys=True,
        )
        row = conn.execute("SELECT * FROM review_actions WHERE id=?", (action_id,)).fetchone()
        if row and row["status"] in {"APPROVED", "SAVED", "REJECTED"}:
            prior = conn.execute(
                "SELECT request FROM review_decisions WHERE action_id=?", (action_id,)
            ).fetchone()
            if prior and prior[0] == request:
                return  # Recover authorization recorded before a graph/process crash.
        if not row or row["status"] != "PENDING" or row["expires"] <= time.time():
            raise ValueError("Review is missing, expired or resolved")
        if (expected_digest is not None and expected_digest != row["digest"]) or (
            expected_version is not None and expected_version != row["version"]
        ):
            raise ValueError("Stale review payload/version")
        if decision != "reject" and json.loads(row["revisions"]) != current_revisions:
            raise ValueError("Evidence changed; start a new proposal")
        if decision not in {"approve", "edit", "reject"}:
            raise ValueError("Unknown review decision")
        payload = row["payload"]
        version = row["version"]
        if decision == "edit":
            if not title or not markdown:
                raise ValueError("Edit requires a complete payload")
            payload = self.payload(row["thread_id"], title, markdown, current_revisions)
            version += 1
        conn.execute(
            "UPDATE review_actions SET status=?,payload=?,digest=?,version=? WHERE id=?",
            (
                "REJECTED" if decision == "reject" else "APPROVED",
                payload,
                sha256(payload.encode()).hexdigest(),
                version,
                action_id,
            ),
        )
        conn.execute("INSERT INTO review_decisions VALUES (?,?)", (action_id, request))

    def recorded_decision(self, action_id):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT request FROM review_decisions WHERE action_id=?", (action_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_reviewed(self, thread_id, title, markdown, revisions):
        payload = self.payload(thread_id, title, markdown, revisions)
        digest = sha256(payload.encode()).hexdigest()
        canonical = json.dumps([thread_id, title, markdown], ensure_ascii=False)
        brief_id = sha256(canonical.encode()).hexdigest()[:32]
        with self.connect() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT * FROM review_actions WHERE thread_id=? AND digest=? "
                "AND status IN ('APPROVED','SAVED') ORDER BY rowid DESC",
                (thread_id, digest),
            ).fetchall()
            if not rows:
                raise PermissionError("No exact-action approval exists")
            row = rows[0]
            if row["status"] == "SAVED":
                return row["brief_id"]  # Reconcile a committed write after an ambiguous response.
            if row["expires"] <= time.time():
                raise PermissionError("Approval expired")
            lineage = self.commit_guard(conn, thread_id) if self.commit_guard is not None else {}
            lineage = lineage or {}
            conn.execute(
                "INSERT OR IGNORE INTO briefs (id,thread_id,title,markdown) VALUES (?,?,?,?)",
                (brief_id, thread_id, title, markdown),
            )
            conn.execute(
                "UPDATE review_actions SET status='SAVED',brief_id=? WHERE id=?",
                (brief_id, row["id"]),
            )
            conn.execute(
                "INSERT OR IGNORE INTO artifact_lineage VALUES (?,?,?,?,?,?,?)",
                (
                    brief_id,
                    row["id"],
                    thread_id,
                    lineage.get("job_id"),
                    self._trace.get(),
                    json.dumps(revisions, sort_keys=True),
                    "northstar-eval-v1",
                ),
            )
        return brief_id

    def lineage(self, brief_id):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM artifact_lineage WHERE brief_id=?", (brief_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["evidence_revisions"] = json.loads(result["evidence_revisions"])
        return result
