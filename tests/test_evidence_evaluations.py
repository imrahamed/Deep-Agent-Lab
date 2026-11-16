from pathlib import Path

import pytest

from deep_agent_lab.evaluation import (
    calibration,
    load_cases,
    regression_gate,
    retrieval_metrics,
    run_evaluation,
)
from deep_agent_lab.evidence import (
    Claim,
    PolicyFact,
    Reference,
    contradictions,
    extractive_verdict,
    validate_references,
)
from deep_agent_lab.knowledge import fixture_search
from deep_agent_lab.retrieval import adaptive_search, bm25, cosine, hybrid, rerank, vector_rank


def test_provenance_and_valid_but_irrelevant_citations():
    row = fixture_search("production restore", 1)[0]
    registry = {row.id: row}
    reference = Reference(evidence_id=row.id, revision=row.revision, quote=row.excerpt)
    claim = Claim(
        text="The database operations lead approves production restores.", references=[reference]
    )
    assert extractive_verdict(claim, registry).label == "supported"
    for text in [
        "The database operations lead never approves production restores.",
        "The restore approver automatically becomes Incident Commander.",
        "The database operations lead approves production restores only for staging.",
    ]:
        assert (
            extractive_verdict(claim.model_copy(update={"text": text}), registry).label
            == "insufficient"
        )
    for updates, code in [
        ({"revision": "5"}, "revision_mismatch"),
        ({"evidence_id": "fake"}, "unknown_evidence"),
        ({"quote": "fabricated"}, "excerpt_not_in_source"),
    ]:
        bad = Claim(text=claim.text, references=[reference.model_copy(update=updates)])
        assert code in validate_references(bad, registry)
    other = row.model_copy(update={"id": "conflict", "revision": "5", "excerpt": "Different rule."})
    registry[other.id] = other
    facts = [
        PolicyFact(
            subject="restore",
            predicate="approver",
            value=value,
            scope="production",
            evidence_id=source.id,
            revision=source.revision,
        )
        for source, value in [(row, "DB lead"), (other, "Recovery manager")]
    ]
    assert len(contradictions(facts, registry)) == 1


def test_rankers_reformulation_and_reranking():
    rows = fixture_search("restore incident access recovery", 5)
    lexical = bm25("production restore", rows)
    assert lexical[0]["_id"] == "northstar-restore"
    vectors = {"northstar-restore": [1, 0], "northstar-incident": [0, 1]}
    semantic = vector_rank([0.8, 0.2], vectors)
    assert semantic[0]["_id"] == "northstar-restore"
    assert hybrid(lexical, semantic)[0]["_id"] == "northstar-restore"
    with pytest.raises(ValueError):
        cosine([0, 0], [1, 1])
    with pytest.raises(ValueError):
        hybrid([], [], k=0)
    assert rerank("commander", rows, lambda q, text: float(q in text))[0].id == "northstar-incident"
    hits, queries = adaptive_search(
        "unknown", lambda q: [1] if q == "restore" else [], lambda q: "restore"
    )
    assert hits == [1] and len(queries) == 2
    assert adaptive_search("missing", lambda q: [], lambda q: q)[1] == ["missing"]


def test_actual_agent_evaluations_and_metrics(tmp_path):
    dataset = Path(__file__).resolve().parents[1] / "data/evaluation/northstar.jsonl"
    report = run_evaluation(load_cases(dataset), tmp_path)
    assert report["kind"] == "measured" and report["summary"]["count"] == 8
    assert report["summary"]["failures"] == []
    assert all(t["input_tokens"] is None and t["claim_support"] is None for t in report["trials"])
    assert regression_gate(report, report)
    metrics = retrieval_metrics({"a", "b", "c"}, ["x", "a", "y", "b", "z"], 5)
    assert metrics["recall"] == 2 / 3 and metrics["precision"] == 2 / 5 and metrics["mrr"] == 1 / 2
    assert retrieval_metrics(set(), [], 5)["recall"] is None
    assert (
        calibration(["supported", "contradicted"], ["supported", "supported"])["agreement"] == 0.5
    )
