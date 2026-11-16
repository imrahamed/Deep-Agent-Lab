from deep_agent_lab.settings import Settings


def test_live_mode_reuses_credentials_and_keeps_separate_index(tmp_path, monkeypatch):
    shared = tmp_path / "rag.env"
    shared.write_text(
        "POSTGRES_DSN=postgresql://rag_user:example@db.test/rag\n"
        "OPENSEARCH_URL=https://search.test\n"
        "OPENSEARCH_INDEX=rag-lab-v1\n"
        "OLLAMA_URL=http://localhost:11434\n"
        "LANGFUSE_ENABLED=true\n"
        "LANGFUSE_PUBLIC_KEY=pk-example\n"
        "LANGFUSE_SECRET_KEY=sk-example\n"
        "LANGFUSE_CAPTURE_CONTENT=true\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.delenv("OPENSEARCH_INDEX", raising=False)
    monkeypatch.delenv("LANGFUSE_CAPTURE_CONTENT", raising=False)
    settings = Settings(
        _env_file=None,
        deep_lab_mode="live",
        rag_lab_env_file=shared,
        ollama_url="http://localhost:20000",
    )

    assert settings.postgres_dsn.get_secret_value().endswith("@db.test/rag")
    assert str(settings.opensearch_url) == "https://search.test/"
    assert settings.opensearch_index == "deep-agent-lab-v1"
    assert str(settings.ollama_url) == "http://localhost:20000/"
    assert settings.langfuse_enabled
    assert settings.langfuse_secret_key.get_secret_value() == "sk-example"
    assert not settings.langfuse_capture_content


def test_live_requires_valid_inherited_settings(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="Could not read"):
        Settings(_env_file=None, deep_lab_mode="live", langfuse_enabled=False,
                 rag_lab_env_file=tmp_path / "missing.env")
