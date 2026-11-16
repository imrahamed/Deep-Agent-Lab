"""Unit tests for RAG retrieval, hydration and index validation."""

from types import SimpleNamespace
from typing import Any

import pytest

from deep_agent_lab.rag.models import SearchRequest
from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.rag.search import SearchIndex


def test_active_hydration_preserves_source_revision_and_drops_stale_ids():
    # Bypass __init__ to test retrieval without external services.
    service = RagService.__new__(RagService)

    # Test-only dynamic fakes; production types remain unchanged.
    stub: Any = service

    stub.settings = SimpleNamespace(retrieval_candidates=30)

    stub.index = SimpleNamespace(
        validate_profile=lambda: None,
        keyword=lambda query, count: [
            {"_id": "orphan", "_score": 100},
            {"_id": "active", "_score": 1},
        ],
        semantic=lambda vector, count: [{"_id": "active", "_score": 0.1}],
    )

    stub.ollama = SimpleNamespace(embed=lambda texts, purpose: [[1.0, 0.0]])

    stub.db = SimpleNamespace(
        hydrate=lambda ids: {
            "active": {
                "chunk_id": "active",
                "document_id": "bkp",
                "title": "Backup",
                "source": "BKP-7",
                "position": 0,
                "text": "Current rule",
                "revision": "5",
            }
        }
    )

    hits = service._search(SearchRequest(query="restore", mode="hybrid"))

    assert len(hits) == 1
    assert hits[0].chunk_id == "active"
    assert hits[0].revision == "5"


def test_embedding_profile_and_partial_search_are_rejected():
    # Construct without connecting to OpenSearch.
    index = SearchIndex.__new__(SearchIndex)

    stub: Any = index

    stub.index = "test"

    stub.settings = SimpleNamespace(
        embedding_profile={
            "model": "current",
            "dimensions": 2,
        }
    )

    # Match the real request(method, path, **kwargs) signature.
    stub.request = lambda method, path, **kwargs: {
        "test": {
            "mappings": {
                "_meta": {
                    "embedding": {
                        "model": "old",
                        "dimensions": 2,
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match="differs"):
        index.validate_profile()

    with pytest.raises(RuntimeError, match="incomplete"):
        SearchIndex.hits({"timed_out": True})
