from hashlib import sha256
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, computed_field

from deep_agent_lab.rag.models import SearchRequest
from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.settings import SearchMode, Settings

Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Limit = Annotated[int, Field(ge=1, le=5)]
ASSETS = Path(__file__).parent / "assets"


class Evidence(BaseModel):
    id: str
    title: str
    source: str
    position: int
    excerpt: str
    revision: str = "fixture-v1"

    @computed_field
    @property
    def citation(self) -> str:
        token = sha256(self.id.encode()).hexdigest()[:12]
        return f"[[{token}]]"


def load_policy_evidence(directory: Path) -> list[Evidence]:
    """Load actual policy files with content-derived revision and passage identifiers."""
    from deep_agent_lab.rag.chunking import chunk_text
    from deep_agent_lab.rag.loaders import load_file

    rows = []
    for path in sorted(directory.glob("*.md")):
        title, source, content = load_file(path)
        revision = sha256(content.encode()).hexdigest()
        for position, excerpt in enumerate(chunk_text(content, 1400, 200)):
            key = sha256(f"{path.name}:{revision}:{position}".encode()).hexdigest()
            rows.append(
                Evidence(
                    id=key,
                    title=title,
                    source=source,
                    position=position,
                    excerpt=excerpt,
                    revision=revision,
                )
            )
    if not rows:
        raise ValueError("No policy Markdown files found")
    return rows


def local_search(directory: Path, query: str, top_k: int = 3) -> list[Evidence]:
    """A real lexical baseline over files read on every invocation."""
    from deep_agent_lab.foundations import SearchArgs
    from deep_agent_lab.retrieval import bm25

    request = SearchArgs(query=query, top_k=top_k)
    rows = load_policy_evidence(directory)
    registry = {row.id: row for row in rows}
    return [registry[hit["_id"]] for hit in bm25(request.query, rows)[: request.top_k]]


def search_knowledge(
    settings: Settings,
    query: Query,
    mode: SearchMode = "hybrid",
    top_k: Limit = 4,
    *,
    rag: RagService | None = None,
) -> list[Evidence]:
    request = SearchRequest(query=query, mode=mode, top_k=top_k)
    if rag is None:
        with RagService(settings) as service:
            hits = service.search(request)
    else:
        hits = rag.search(request)
    return [
        Evidence(
            id=hit.chunk_id,
            title=hit.title,
            source=hit.source,
            position=hit.position,
            excerpt=hit.text[:1400],
            revision=hit.revision,
        )
        for hit in hits
    ]
