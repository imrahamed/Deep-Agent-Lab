import hashlib
import json
import logging
from contextlib import contextmanager
from pathlib import Path

from deep_agent_lab.rag.chunking import chunk_text
from deep_agent_lab.rag.db import Database
from deep_agent_lab.rag.loaders import load_file
from deep_agent_lab.rag.models import Hit, SearchRequest
from deep_agent_lab.rag.ollama import Ollama
from deep_agent_lab.rag.search import SearchIndex, reciprocal_rank_fusion
from deep_agent_lab.settings import Settings
from deep_agent_lab.tracing import Tracing

logger = logging.getLogger(__name__)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RagService:
    def __init__(self, settings: Settings, tracing: Tracing | None = None):
        self.settings = settings
        self.owns_tracing = tracing is None
        self.tracing = tracing if tracing is not None else Tracing(settings)
        self.db = Database(settings, self.tracing)
        self.ollama = Ollama(settings, self.tracing)
        self.index = SearchIndex(settings, self.tracing)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        try:
            try:
                self.ollama.close()
            finally:
                self.index.close()
        finally:
            if self.owns_tracing:
                self.tracing.close()

    def initialize(self):
        # Check the embedding shape before creating a remote index.
        self.ollama.embed(["Embedding dimension check"])
        self.index.initialize()
        self.db.initialize()

    def health(self, check_tracing: bool = False) -> dict:
        results = {}
        for name, check in [
            ("postgres", self.db.health),
            ("opensearch", self.index.health),
            ("ollama", self.ollama.health),
        ]:
            try:
                results[name] = check()
            except Exception as error:
                # Connection exceptions may include credentials; do not return their strings.
                results[name] = {"status": "error", "error_type": type(error).__name__}
        tracing = self.tracing.status(check_connection=check_tracing)
        healthy = all(x["status"] == "ok" for x in results.values())
        if check_tracing and tracing["status"] == "error":
            healthy = False
        return {
            "status": "ok" if healthy else "error",
            "services": results,
            "tracing": tracing,
        }

    @contextmanager
    def document_lock(self, document_id: str):
        with self.db.connect() as connection:
            # A session lock spans SQL commit AND search cleanup. Other documents can ingest.
            connection.execute("SELECT set_config('lock_timeout', '30s', false)")
            locking_key = f"deep_agent_lab:{document_id}"
            connection.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (locking_key,))
            connection.commit()
            yield connection
            # Closing the connection releases the session lock, also on exceptions.

    def ingest(self, title: str, source: str, content: str, force: bool = False) -> dict:
        if not content.strip():
            raise ValueError("Cannot ingest empty content")
        document_id = digest(source)
        with self.tracing.span(
            "rag.ingest",
            input={"title": title, "source": source},
            metadata={"document_id": document_id, "chars": len(content), "force": force},
        ) as span:
            with self.document_lock(document_id) as connection:
                result = self._ingest(connection, document_id, title, source, content, force)
            result["trace_id"] = span.trace_id
            span.update(output=result, metadata=result)
            return result

    def ingest_file(self, path: Path, force: bool = False) -> dict:
        with self.tracing.span("rag.ingest_file", input=str(path)) as span:
            with self.tracing.span("rag.load_file"):
                document = load_file(path)
            result = self.ingest(*document, force=force)
            result["trace_id"] = span.trace_id
            span.update(metadata={"document_id": result["document_id"], "status": result["status"]})
            return result

    def reindex(self, document_id: str) -> dict:
        with self.tracing.span("rag.reindex", metadata={"document_id": document_id}) as span:
            result = self._reindex(document_id)
            result["trace_id"] = span.trace_id
            span.update(output=result, metadata=result)
            return result

    def _reindex(self, document_id: str) -> dict:
        # Load the latest canonical body under the same lock used by normal ingestion.
        with self.document_lock(document_id) as connection:
            row = connection.execute(
                "SELECT * FROM deep_agent_lab.rag_documents WHERE id=%s", (document_id,)
            ).fetchone()
            if not row:
                raise ValueError("Document no longer exists")
            return self._ingest(
                connection, document_id, row["title"], row["source"], row["content"], force=True
            )

    def _ingest(self, connection, document_id, title, source, content, force):
        revision = digest(json.dumps([title, content, self.settings.pipeline_version]))
        current = connection.execute(
            "SELECT revision FROM deep_agent_lab.rag_documents WHERE id=%s", (document_id,)
        ).fetchone()
        if current and current["revision"] == revision and not force:
            return {"document_id": document_id, "status": "unchanged"}
        self.index.validate_profile()
        with self.tracing.span("rag.chunk", metadata={"input_chars": len(content)}) as span:
            texts = chunk_text(content, self.settings.chunk_size, self.settings.chunk_overlap)
            span.update(
                metadata={
                    "chunks": len(texts),
                    "chunk_size": self.settings.chunk_size,
                    "overlap": self.settings.chunk_overlap,
                }
            )
        vectors = []
        for start in range(0, len(texts), self.settings.embed_batch_size):
            vectors.extend(self.ollama.embed(texts[start : start + self.settings.embed_batch_size]))
        chunks = [
            {
                "id": digest(f"{document_id}:{revision}:{i}"),
                "document_id": document_id,
                "revision": revision,
                "title": title,
                "text": text,
                "embedding": vector,
            }
            for i, (text, vector) in enumerate(zip(texts, vectors, strict=True))
        ]
        # Index first. A SQL rollback leaves only orphan search records; hydration excludes them.
        self.index.write(chunks)
        with self.tracing.span("postgres.persist", metadata={"chunk_count": len(chunks)}):
            connection.execute(
                "INSERT INTO deep_agent_lab.rag_documents(id,title,source,content,revision) "
                "VALUES(%s,%s,%s,%s,%s) "
                "ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title, source=EXCLUDED.source, "
                "content=EXCLUDED.content, revision=EXCLUDED.revision, updated_at=now()",
                (document_id, title, source, content, revision),
            )
            connection.execute(
                "DELETE FROM deep_agent_lab.rag_chunks WHERE document_id=%s", (document_id,)
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO deep_agent_lab.rag_chunks(id,document_id,position,content) "
                    "VALUES(%s,%s,%s,%s)",
                    [
                        (chunk["id"], document_id, i, chunk["text"])
                        for i, chunk in enumerate(chunks)
                    ],
                )
            connection.commit()
        cleanup_pending = False
        try:
            self.index.cleanup(document_id, revision)
        except Exception as error:
            cleanup_pending = True
            logger.warning("Search cleanup pending (%s); run reindex", type(error).__name__)
        return {
            "document_id": document_id,
            "status": "indexed",
            "chunks": len(chunks),
            "cleanup_pending": cleanup_pending,
        }

    def search(self, request: SearchRequest) -> list[Hit]:
        with self.tracing.span(
            "rag.retrieve",
            as_type="retriever",
            input=request.model_dump(),
            metadata={
                "mode": request.mode,
                "top_k": request.top_k,
                "query_chars": len(request.query),
            },
        ) as span:
            hits = self._search(request)
            span.update(
                output=[hit.model_dump() for hit in hits],
                metadata={
                    "hit_count": len(hits),
                    "chunk_ids": [hit.chunk_id for hit in hits],
                    "scores": [hit.score for hit in hits],
                },
            )
            return hits

    def _search(self, request: SearchRequest) -> list[Hit]:
        self.index.validate_profile()
        count = max(request.top_k, self.settings.retrieval_candidates)
        rankings = []
        if request.mode in {"keyword", "hybrid"}:
            rankings.append(self.index.keyword(request.query, count))
        if request.mode in {"semantic", "hybrid"}:
            vector = self.ollama.embed([request.query], purpose="query")[0]
            rankings.append(self.index.semantic(vector, count))
        ranking = reciprocal_rank_fusion(rankings) if len(rankings) == 2 else rankings[0]
        rows = self.db.hydrate([item["_id"] for item in ranking])
        # SQL controls which document revisions are visible, not the search index.
        return [
            Hit(**rows[item["_id"]], score=item["_score"])
            for item in ranking
            if item["_id"] in rows
        ][: request.top_k]
