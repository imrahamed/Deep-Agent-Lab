from deep_agent_lab.evaluation import EvalCase, grade
from deep_agent_lab.knowledge import fixture_search
from deep_agent_lab.service import RunResult


def test_live_grading_uses_explicit_sources_and_retains_exact_chunk_ids():
    row = fixture_search("restore", 1)[0].model_copy(
        update={
            "id": "revisioned-chunk-sha256",
            "revision": "content-revision",
            "source": "file:///corpus/backup-policy.md",
        }
    )
    case = EvalCase(
        id="live",
        prompt="approver?",
        expected_evidence=["northstar-restore"],
        expected_sources=["backup-policy.md"],
        required_phrases=["database operations lead"],
    )
    result = RunResult(
        thread_id="live",
        status="completed",
        evidence=[row],
        answer="The database operations lead approves production restores. " + row.citation,
    )
    observed = grade(case, result, live=True)
    assert observed["task_success"] and observed["evidence_recall"] == 1
    assert observed["grading_basis"] == "document_source"
    assert observed["evidence_ids"] == ["revisioned-chunk-sha256"]
    result.evidence = [row.model_copy(update={"source": "file:///corpus/unrelated.md"})]
    assert not grade(case, result, live=True)["task_success"]
