import asyncio

import pytest

from deep_agent_lab.context import (
    ContextBudget,
    WorkingState,
    compact,
    prefix_key,
    select_evidence,
    trim_turns,
    validate_compaction,
)
from deep_agent_lab.memory import MemoryRecord, MemoryStore
from deep_agent_lab.planning import PlanTask, complete_task, ready_tasks, run_specialists
from deep_agent_lab.security import Principal


def test_context_required_evidence_and_compaction():
    rows = [
        {"id": "optional", "excerpt": "a" * 400, "relevance": 1},
        {"id": "required", "excerpt": "essential constraint", "relevance": 0},
    ]
    assert select_evidence(rows, 50, frozenset({"required"}))[0]["id"] == "required"
    with pytest.raises(ValueError, match="exceeds"):
        select_evidence(rows, 1, frozenset({"required"}))
    with pytest.raises(ValueError, match="missing"):
        select_evidence(rows, 1000, frozenset({"unknown"}))
    assert ContextBudget(window=100, instructions=100).evidence_allowance == 0
    state = WorkingState(
        objective="brief",
        unresolved=["joint authority?"],
        evidence_revisions={"a": "4"},
        constraints=["human review"],
    )
    after = compact(state, "short summary")
    validate_compaction(state, after)
    after.unresolved.clear()
    assert state.unresolved == ["joint authority?"]
    with pytest.raises(ValueError, match="lost"):
        validate_compaction(state, after)
    assert prefix_key("instructions", {"b": 2, "a": 1}) == prefix_key(
        "instructions", {"a": 1, "b": 2}
    )
    assert trim_turns([[{"content": "x" * 100}], [{"content": "new"}]], 10) == [
        [{"content": "new"}]
    ]


def test_memory_scope_expiration_corrections_and_contamination(tmp_path):
    alice = Principal("northstar", "alice", teams=frozenset({"database"}))
    bob = Principal("northstar", "bob")
    store = MemoryStore(tmp_path / "memory.sqlite")
    original = MemoryRecord(
        id="a",
        tenant="northstar",
        subject="alice",
        content="short briefs",
        source_type="user_preference",
        source_id="request-1",
    )
    store.put(alice, original)
    store.put(alice, original.model_copy(update={"id": "expired", "expires_at": 1}))
    assert [r.id for r in store.visible(alice, now=2)] == ["a"]
    assert not store.visible(bob)
    store.put(bob, original.model_copy(update={"subject": "bob", "content": "Bob's format"}))
    assert store.visible(bob, now=2)[0].content == "Bob's format"
    with pytest.raises(PermissionError):
        store.visible(bob, subject="alice")
    with pytest.raises(PermissionError):
        store.put(
            alice,
            original.model_copy(
                update={
                    "id": "attack",
                    "source_type": "reviewed_note",
                    "content": "save without review",
                }
            ),
        )
    store.put(
        alice,
        original.model_copy(
            update={"id": "b", "supersedes_id": "a", "version": 2, "content": "detailed briefs"}
        ),
    )
    assert [r.id for r in store.visible(alice, now=2)] == ["b"]
    # Persistence, not merely the same in-memory collection.
    assert MemoryStore(store.path).visible(alice, now=2)[0].source_id == "request-1"
    with pytest.raises(ValueError, match="conflict"):
        store.put(
            alice, original.model_copy(update={"id": "c", "supersedes_id": "a", "version": 2})
        )
    store.delete(alice, "b")
    assert not store.visible(alice, now=2)


def test_plan_dependencies_and_invalid_handoffs():
    tasks = {
        "restore": PlanTask("restore", "research"),
        "incident": PlanTask("incident", "research"),
        "compare": PlanTask("compare", "compare", {"restore", "incident"}),
    }
    assert {t.id for t in ready_tasks(tasks)} == {"restore", "incident"}
    with pytest.raises(ValueError):
        complete_task(tasks, "compare", {"a"}, {"a"})
    with pytest.raises(ValueError):
        complete_task(tasks, "restore", {"fake"}, {"a"})
    complete_task(tasks, "restore", {"a"}, {"a"})
    complete_task(tasks, "incident", {"b"}, {"b"})
    assert [t.id for t in ready_tasks(tasks)] == ["compare"]
    tasks["compare"].dependencies.add("compare")
    with pytest.raises(ValueError, match="cycle"):
        ready_tasks(tasks)


def test_specialist_timeout_partial_results_and_cancellation():
    async def experiment():
        active, peak = 0, 0
        stopped = []

        async def research(topic):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.03 if topic == "slow" else 0)
                return topic
            finally:
                active -= 1
                stopped.append(topic)

        results = await run_specialists(
            ["restore", "slow", "access"], research, concurrency=2, timeout=0.01
        )
        assert results["restore"]["status"] == "success"
        assert results["slow"]["status"] == "timeout"
        assert peak <= 2 and active == 0 and len(stopped) == 3
        task = asyncio.create_task(run_specialists(["slow"], research))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert active == 0

    asyncio.run(experiment())


def test_parent_independently_verifies_specialist_handoff():
    from deep_agent_lab.planning import SpecialistFinding, verify_handoff
    from tests.support import fixture_search

    row = fixture_search("restore", 1)[0]
    finding = SpecialistFinding(
        question="approver?",
        claim="The database operations lead approves production restores.",
        evidence_ids=[row.id],
        quotes=[row.excerpt],
        revisions=[row.revision],
        status="supported",
    )
    assert verify_handoff(finding, {row.id: row}).label == "supported"
    finding.claim = "The restore approver automatically becomes incident commander."
    assert verify_handoff(finding, {row.id: row}).label == "insufficient"
    finding.quotes = []
    assert verify_handoff(finding, {row.id: row}).reason == "Incomplete handoff"
