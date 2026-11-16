import hashlib
import json
from pathlib import Path
from typing import ClassVar, Literal

from dotenv import dotenv_values
from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    inherited_fields: ClassVar[tuple[str, ...]] = (
        "postgres_dsn",
        "opensearch_url",
        "opensearch_username",
        "opensearch_password",
        "opensearch_ca_cert",
        "ollama_url",
        "ollama_embed_model",
        "embedding_dimensions",
        "embed_document_prefix",
        "embed_query_prefix",
        "chunk_size",
        "chunk_overlap",
        "embed_batch_size",
        "retrieval_candidates",
        "request_timeout_seconds",
        "langfuse_enabled",
        "langfuse_public_key",
        "langfuse_secret_key",
        "langfuse_base_url",
        "langfuse_environment",
        "langfuse_timeout_seconds",
    )

    deep_lab_mode: Literal["demo", "live"] = "demo"
    deep_lab_state_dir: Path = Path(".deep-lab")
    rag_lab_env_file: Path | None = None
    postgres_dsn: SecretStr | None = None
    opensearch_url: AnyHttpUrl | None = None
    opensearch_username: str | None = None
    opensearch_password: SecretStr | None = None
    opensearch_index: str = Field(
        default="deep-agent-lab-v1",
        pattern=r"^deep-agent-lab-[a-z0-9_-]+$",
    )
    opensearch_ca_cert: Path | None = None
    ollama_url: AnyHttpUrl = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen3.5:latest"
    ollama_context_tokens: int = Field(default=16384, ge=4096)
    ollama_embed_model: str = "nomic-embed-text"
    embed_document_prefix: str = "search_document: "
    embed_query_prefix: str = "search_query: "
    embedding_dimensions: int = Field(default=768, ge=1)
    chunk_size: int = Field(default=1400, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)
    embed_batch_size: int = Field(default=16, ge=1, le=128)
    retrieval_candidates: int = Field(default=30, ge=10, le=1000)
    context_evidence_tokens: int = Field(default=3000, ge=128)
    request_timeout_seconds: float = Field(default=180, gt=0)
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: AnyHttpUrl = "https://cloud.langfuse.com"
    langfuse_environment: str = "development"
    langfuse_capture_content: bool = False
    langfuse_timeout_seconds: int = Field(default=5, ge=1, le=60)

    @model_validator(mode="before")
    @classmethod
    def inherit_rag_lab_settings(cls, values: dict) -> dict:
        source = values.get("rag_lab_env_file")
        if values.get("deep_lab_mode") != "live" or not source:
            return values
        try:
            with Path(source).expanduser().open(encoding="utf-8-sig") as stream:
                rag_values = dotenv_values(stream=stream)
        except (OSError, UnicodeError):
            raise ValueError("Could not read RAG_LAB_ENV_FILE") from None
        inherited = {
            name: rag_values[name.upper()]
            for name in cls.inherited_fields
            if rag_values.get(name.upper()) is not None
        }
        return {**inherited, **values}

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.deep_lab_mode == "live" and (not self.postgres_dsn or not self.opensearch_url):
            raise ValueError("Live mode requires POSTGRES_DSN and OPENSEARCH_URL")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")
        if bool(self.opensearch_username) != bool(self.opensearch_password):
            raise ValueError("Set both OpenSearch username and password, or neither")
        if self.opensearch_url and (self.opensearch_url.username or self.opensearch_url.password):
            raise ValueError("Use OPENSEARCH_USERNAME/PASSWORD instead of URL credentials")
        if self.langfuse_base_url.username or self.langfuse_base_url.password:
            raise ValueError("Use Langfuse project API keys instead of URL credentials")
        if self.langfuse_enabled and not (self.langfuse_public_key and self.langfuse_secret_key):
            raise ValueError("Enabled Langfuse tracing requires both project API keys")
        return self

    @property
    def state_dir(self) -> Path:
        return self.deep_lab_state_dir.resolve() / self.deep_lab_mode

    @property
    def embedding_profile(self) -> dict:
        # Changing a model with the same dimension still changes the vector space.
        return {
            "model": self.ollama_embed_model,
            "dimensions": self.embedding_dimensions,
            "document_prefix": self.embed_document_prefix,
            "query_prefix": self.embed_query_prefix,
        }

    @property
    def pipeline_version(self) -> str:
        value = {
            **self.embedding_profile,
            "size": self.chunk_size,
            "overlap": self.chunk_overlap,
            "chunker": "characters-v1",
        }
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


SearchMode = Literal["keyword", "semantic", "hybrid"]
