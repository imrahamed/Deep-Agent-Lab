"""SQLite durable jobs with expiring ownership, retries and fenced local writes."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from deep_agent_lab.security import Principal, authorize


class LeaseLost(RuntimeError):
    pass


class JobStore:
    def __init__(self, path: Path, *, clock=time.time):
        self.path, self.clock = path, clock
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, owner TEXT NOT NULL,
                thread_id TEXT NOT NULL UNIQUE, input TEXT NOT NULL, status TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0, token TEXT, lease_until REAL,
                deadline REAL NOT NULL, available REAL NOT NULL, result TEXT, error TEXT,
                max_attempts INTEGER NOT NULL DEFAULT 3
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def submit(self, principal: Principal, prompt: str, *, job_id=None, ttl=3600, max_attempts=3):
        if "research" not in principal.permissions:
            raise PermissionError("Research permission required")
        if not prompt.strip() or len(prompt) > 4000 or ttl <= 0 or not 1 <= max_attempts <= 10:
            raise ValueError("Invalid job policy")
        job_id = job_id or uuid4().hex
        # No model-controlled tenant or checkpoint identifier.
        from hashlib import sha256

        thread = sha256(f"{principal.tenant}:{principal.user}:{job_id}".encode()).hexdigest()
        body = json.dumps({"prompt": prompt}, sort_keys=True)
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO jobs "
                "(id,tenant,owner,thread_id,input,status,deadline,available,max_attempts) "
                "VALUES (?,?,?,?,?,'QUEUED',?,?,?)",
                (
                    job_id,
                    principal.tenant,
                    principal.user,
                    thread,
                    body,
                    self.clock() + ttl,
                    self.clock(),
                    max_attempts,
                ),
            )
            row = dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
        authorize(principal, row["tenant"], row["owner"], "research")
        if row["input"] != body:
            raise ValueError("Idempotency key reused with different input")
        return row

    def get(self, principal: Principal, job_id: str, *, permission="research"):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise ValueError("Unknown job")
        authorize(principal, row["tenant"], row["owner"], permission)
        return dict(row)

    def claim(self, *, lease_seconds=30, job_id=None, review=False):
        """Trusted worker operation; API callers use get() before selecting a specific job."""
        if lease_seconds <= 0:
            raise ValueError("Lease must be positive")
        now = self.clock()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE jobs SET status='FAILED',error='deadline_or_attempts' "
                "WHERE status IN ('QUEUED','RETRY_PENDING','RUNNING','WAITING_REVIEW') "
                "AND (deadline<=? OR (attempt>=max_attempts AND status!='WAITING_REVIEW' AND "
                "(status!='RUNNING' OR lease_until<=?)))",
                (now, now),
            )
            states = (
                "status='WAITING_REVIEW'"
                if review
                else (
                    "(status IN ('QUEUED','RETRY_PENDING') OR "
                    "(status='RUNNING' AND lease_until<=?))"
                )
            )
            parameters = [] if review else [now]
            condition = ""
            if job_id is not None:
                condition = " AND id=?"
                parameters.append(job_id)
            row = db.execute(
                "SELECT * FROM jobs WHERE "
                + states
                + condition
                + " AND deadline>? AND available<=? ORDER BY available,id LIMIT 1",
                (*parameters, now, now),
            ).fetchone()
            if row is None:
                return None
            token = uuid4().hex
            db.execute(
                "UPDATE jobs SET status='RUNNING',token=?,lease_until=?,attempt=attempt+? "
                "WHERE id=?",
                (token, min(now + lease_seconds, row["deadline"]), int(not review), row["id"]),
            )
            return dict(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def fence(self, db, job_id: str, token: str):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        now = self.clock()
        if (
            not row
            or row["status"] != "RUNNING"
            or row["token"] != token
            or row["lease_until"] <= now
            or row["deadline"] <= now
        ):
            raise LeaseLost("Job is cancelled, expired, or owned by another attempt")
        return dict(row)

    def transition(self, job_id, token, status, *, result=None):
        if status not in {"WAITING_REVIEW", "COMPLETED", "FAILED"}:
            raise ValueError("Invalid worker transition")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.fence(db, job_id, token)
            db.execute(
                "UPDATE jobs SET status=?,result=?,token=NULL,lease_until=NULL WHERE id=?",
                (status, result, job_id),
            )

    def renew(self, job_id, token, *, lease_seconds=30):
        if lease_seconds <= 0:
            raise ValueError("Lease must be positive")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.fence(db, job_id, token)
            db.execute(
                "UPDATE jobs SET lease_until=? WHERE id=?",
                (min(self.clock() + lease_seconds, row["deadline"]), job_id),
            )

    def fail(self, job_id, token, *, retryable: bool, code: str, backoff=1):
        if backoff < 0 or code not in {"timeout", "unavailable", "invalid", "internal"}:
            raise ValueError("Invalid retry policy/error code")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.fence(db, job_id, token)
            status = (
                "RETRY_PENDING" if retryable and row["attempt"] < row["max_attempts"] else "FAILED"
            )
            db.execute(
                "UPDATE jobs SET status=?,error=?,available=?,token=NULL,lease_until=NULL "
                "WHERE id=?",
                (status, code, self.clock() + backoff, job_id),
            )

    def cancel(self, principal, job_id):
        self.get(principal, job_id)
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status='CANCELLED',token=NULL,lease_until=NULL "
                "WHERE id=? AND status NOT IN ('COMPLETED','FAILED','CANCELLED')",
                (job_id,),
            )
