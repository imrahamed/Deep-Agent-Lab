from pydantic import BaseModel, Field, field_validator

from deep_agent_lab.settings import SearchMode


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    mode: SearchMode = "hybrid"
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must contain non-whitespace characters")
        return value.strip()


class Hit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str
    position: int
    text: str
    score: float
