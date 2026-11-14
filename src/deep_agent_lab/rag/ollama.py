import math
from typing import Literal

import httpx

from deep_agent_lab.settings import Settings
from deep_agent_lab.tracing import Tracing


class Ollama:
    def __init__(self, settings: Settings, tracing: Tracing | None = None):
        self.settings = settings
        self.tracing = tracing or Tracing()
        self.client = httpx.Client(
            base_url=str(settings.ollama_url).rstrip("/"),
            timeout=settings.request_timeout_seconds,
        )

    def close(self):
        self.client.close()

    def health(self) -> dict:
        response = self.client.get("/api/tags")
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        required = [self.settings.ollama_chat_model, self.settings.ollama_embed_model]
        missing = [
            name for name in required if name not in models and f"{name}:latest" not in models
        ]
        if missing:
            raise RuntimeError("Pull required Ollama models: " + ", ".join(missing))
        return {"status": "ok", "models": models}

    def embed(
        self, texts: list[str], purpose: Literal["document", "query"] = "document"
    ) -> list[list[float]]:
        if not texts:
            return []
        with self.tracing.span(
            f"ollama.embed.{purpose}",
            as_type="embedding",
            model=self.settings.ollama_embed_model,
            input=texts,
            metadata={
                "batch_size": len(texts),
                "input_chars": sum(map(len, texts)),
                "dimensions": self.settings.embedding_dimensions,
            },
        ) as span:
            data = self._embed(texts, purpose)
            span.update(
                usage_details={"input": data["prompt_eval_count"]}
                if "prompt_eval_count" in data
                else {},
                metadata={
                    "total_duration_ns": data.get("total_duration"),
                    "vector_count": len(data["embeddings"]),
                },
            )
            # Never export the vectors; they are large and not needed to debug the call.
            return data["embeddings"]

    def _embed(self, texts: list[str], purpose: str) -> dict:
        prefix = (
            self.settings.embed_query_prefix
            if purpose == "query"
            else self.settings.embed_document_prefix
        )
        response = self.client.post(
            "/api/embed",
            json={
                "model": self.settings.ollama_embed_model,
                "input": [prefix + text for text in texts],
                "truncate": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        vectors = data["embeddings"]
        if len(vectors) != len(texts):
            raise ValueError("Ollama returned the wrong number of embeddings")
        for vector in vectors:
            if len(vector) != self.settings.embedding_dimensions:
                raise ValueError("Embedding dimension mismatch; check EMBEDDING_DIMENSIONS")
            if not all(math.isfinite(x) for x in vector) or not any(vector):
                raise ValueError("Ollama returned an invalid embedding")
        return data
