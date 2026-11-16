import pytest

from deep_agent_lab.knowledge import Evidence
from deep_agent_lab.retrieval import EvidenceAssessment, adaptive_search
from tests.support import fixture_search

QUESTION = "What is the RTO for ZEPHYR-99?"
REWRITE = "ZEPHYR-99 recovery time objective RTO"
FACT = Evidence(
    id="synthetic-zephyr",
    title="Synthetic test fixture",
    source="fixture/zephyr",
    position=0,
    excerpt="ZEPHYR-99 has an RTO of two hours.",
)


def assess(question, evidence):
    assert question == QUESTION
    found = any(row.id == FACT.id and row.excerpt == FACT.excerpt for row in evidence)
    return EvidenceAssessment(
        answerable=found, missing_information=[] if found else ["ZEPHYR-99 RTO fact"]
    )


def test_faithful_rewrite_accumulates_evidence():
    trace = adaptive_search(
        QUESTION,
        lambda query: [FACT] if query == REWRITE else [],
        lambda original, queries, missing: REWRITE,
        assess,
    )
    assert trace.original_question == QUESTION
    assert all("ZEPHYR-99" in query for query in trace.queries_attempted)
    assert trace.answerable and trace.stop_reason == "answerable"
    assert trace.retrieved_evidence == [FACT]


@pytest.mark.parametrize("rows", [[], fixture_search("production restore", 3)])
def test_missing_fact_abstains_even_with_related_documents(rows):
    trace = adaptive_search(
        QUESTION,
        lambda query: rows,
        lambda original, queries, missing: REWRITE,
        assess,
    )
    assert trace.retrieved_evidence == rows
    assert not trace.answerable and trace.missing_information == ["ZEPHYR-99 RTO fact"]
    assert trace.stop_reason == "query_budget_exhausted"
    assert all("ZEPHYR-99" in query for query in trace.queries_attempted)


@pytest.mark.parametrize(
    ("rewrite", "reason"),
    [
        ("production restore", "reformulation_drift"),
        ("", "no_new_query"),
        ("  WHAT is the RTO for ZEPHYR-99?  ", "repeated_query"),
    ],
)
def test_unexecuted_rewrites(rewrite, reason):
    executed = []

    def search(query):
        executed.append(query)
        return []

    trace = adaptive_search(
        QUESTION,
        search,
        lambda original, queries, missing: rewrite,
        assess,
    )
    assert trace.stop_reason == reason and executed == [QUESTION]


def test_budget_and_unique_evidence():
    rows = fixture_search("restore", 1)
    trace = adaptive_search(
        QUESTION,
        lambda query: rows,
        lambda original, queries, missing: f"ZEPHYR-99 RTO attempt {len(queries)}",
        assess,
        max_queries=5,
    )
    assert len(trace.queries_attempted) == 5 and trace.retrieved_evidence == rows
    assert trace.stop_reason == "query_budget_exhausted"


def test_inconsistent_assessments_and_failures():
    with pytest.raises(ValueError, match="requires evidence"):
        adaptive_search(
            QUESTION,
            lambda query: [],
            lambda *args: REWRITE,
            lambda *args: EvidenceAssessment(answerable=True),
        )
    with pytest.raises(ValueError, match="Conflicting"):
        adaptive_search(
            QUESTION,
            lambda query: [FACT, FACT.model_copy(update={"revision": "changed"})],
            lambda *args: REWRITE,
            assess,
        )

    def unavailable(query):
        raise TimeoutError("unavailable")

    with pytest.raises(TimeoutError):
        adaptive_search(QUESTION, unavailable, lambda *args: REWRITE, assess)
    for budget in [0, 6, True]:
        with pytest.raises(ValueError, match="budget"):
            adaptive_search(
                QUESTION, lambda query: [], lambda *args: REWRITE, assess, max_queries=budget
            )


def test_negation_and_scope_drift():
    question = "Who must not approve production restores for BKP-7?"
    trace = adaptive_search(
        question,
        lambda query: [],
        lambda *args: "BKP-7 staging restores",
        lambda *args: EvidenceAssessment(answerable=False, missing_information=["approver"]),
    )
    assert trace.stop_reason == "reformulation_drift"
