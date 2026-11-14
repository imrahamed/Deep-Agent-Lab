import json
import re
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

    @computed_field
    @property
    def citation(self) -> str:
        token = sha256(self.id.encode()).hexdigest()[:12]
        return f"[[{token}]]"


def fixture_search(query: str, top_k: int) -> list[Evidence]:
    rows = [
        Evidence.model_validate(row)
        for row in json.loads((ASSETS / "sample.json").read_text(encoding="utf-8"))
    ]
    stop_words = {"the", "and", "for", "what", "who", "how", "which", "with", "does", "when"}
    terms = set(re.findall(r"[a-z]{3,}", query.lower())) - stop_words
    scored = [
        (len(terms & set(re.findall(r"[a-z]{3,}", row.excerpt.lower()))), row) for row in rows
    ]
    return [row for score, row in sorted(scored, key=lambda item: -item[0]) if score][:top_k]


def search_knowledge(
    settings: Settings,
    query: Query,
    mode: SearchMode = "hybrid",
    top_k: Limit = 4,
    *,
    rag: RagService | None = None,
) -> list[Evidence]:
    if settings.deep_lab_mode == "demo":
        return fixture_search(query, top_k)

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
        )
        for hit in hits
    ]
