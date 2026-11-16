import os

os.environ.setdefault("MPLBACKEND", "Agg")

import pytest

from tests.support import install_runtime


@pytest.fixture(autouse=True)
def isolated_application_services(monkeypatch, request):
    if request.node.path.name == "test_rag_settings.py":
        return
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://unit:unit@localhost/unit")
    monkeypatch.setenv("OPENSEARCH_URL", "http://localhost:9200")
    monkeypatch.delenv("RAG_LAB_ENV_FILE", raising=False)
    install_runtime(monkeypatch)
