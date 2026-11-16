import pytest

from deep_agent_lab.capstone import Northstar
from deep_agent_lab.security import Principal
from deep_agent_lab.service import AgentService, Decision, ReviewRequest, open_checkpointer
from deep_agent_lab.settings import Settings


def test_research_record_uses_verifier_sentence_boundaries():
    from types import SimpleNamespace

    from deep_agent_lab.context import WorkingState
    from deep_agent_lab.knowledge import Evidence
    from deep_agent_lab.service import RunResult

    row = Evidence(
        id="multiline",
        title="Policy",
        source="policy.md",
        position=0,
        excerpt="Approval is required.\n\nValidation follows. Another condition.",
    )
    app = Northstar.__new__(Northstar)
    app.inspect = lambda principal, job: RunResult(
        thread_id="test", status="completed", evidence=[row]
    )
    app.service = SimpleNamespace(
        config=lambda thread: {},
        agent=SimpleNamespace(
            get_state=lambda config: SimpleNamespace(
                values={"working_state": WorkingState(objective="inspect").model_dump()}
            )
        ),
    )
    principal = Principal("northstar", "alice", permissions=frozenset({"research"}))
    record = app.research_record(principal, "job")
    assert record["claims"][0]["claim"]["text"] == "Approval is required."
    assert record["claims"][0]["verdict"]["label"] == "supported"


def test_capstone_scopes_plan_context_review_and_recovery(tmp_path):
    settings = Settings(
        _env_file=None, deep_lab_mode="live", deep_lab_state_dir=tmp_path, langfuse_enabled=False
    )
    alice, bob = Principal("northstar", "alice"), Principal("northstar", "bob")
    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver)
        try:
            app = Northstar(service)
            job = app.submit(
                alice, "Draft and save a readiness brief comparing restore, incident and access."
            )
            pending = app.work(alice, job["id"])
            assert pending.status == "interrupted"
            assert {"northstar-restore", "northstar-incident", "northstar-access"} <= {
                row.id for row in pending.evidence
            }
            with pytest.raises(PermissionError):
                app.inspect(bob, job["id"])
            record = app.research_record(alice, job["id"])
            assert all(t.status == "verified" for t in record["plan"].values())
            assert all(row["verdict"]["label"] == "supported" for row in record["claims"])
            assert record["state"].unresolved and record["context"]
        finally:
            service.close()

    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver)
        try:
            app = Northstar(service)
            review = pending.reviews[0]
            request = ReviewRequest(
                interrupt_id=review.id,
                decisions=[Decision(type="approve")],
                payload_hashes=["wrong"],
                proposal_versions=[1],
            )
            with pytest.raises(ValueError, match="Stale"):
                app.review(alice, job["id"], request)
            request.payload_hashes = review.payload_hashes
            result = app.review(alice, job["id"], request)
            assert len(result.saved_brief_ids) == 1
            assert app.jobs.get(alice, job["id"])["result"] == result.saved_brief_ids[0]
            artifact = app.artifact(alice, job["id"])
            assert artifact["lineage"]["job_id"] == job["id"]
            assert artifact["lineage"]["evidence_revisions"]
            with pytest.raises(ValueError):
                app.review(alice, job["id"], request)
        finally:
            service.close()


def test_recovery_resumes_unfinished_tool_even_when_model_has_partial_text(tmp_path, monkeypatch):
    import time

    from tests.support import DemoModel

    class Crash(BaseException):
        pass

    class ThinkingDemo(DemoModel):
        @staticmethod
        def respond(messages, names):
            response = DemoModel.respond(messages, names)
            if response.tool_calls:
                response.content = "Research is under way."
            return response

    settings = Settings(
        _env_file=None, deep_lab_mode="live", deep_lab_state_dir=tmp_path, langfuse_enabled=False
    )
    alice = Principal("northstar", "alice")
    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver, model=ThinkingDemo())
        try:
            app = Northstar(service)
            job = app.submit(alice, "Who approves a production restore?")
            with monkeypatch.context() as patch:
                patch.setattr(
                    "deep_agent_lab.agent.search_knowledge",
                    lambda *a, **kw: (_ for _ in ()).throw(Crash()),
                )
                with pytest.raises(Crash):
                    app.work(alice, job["id"])
            snapshot = service.agent.get_state(service.config(job["thread_id"]))
            assert (
                snapshot.next
                and service.inspect(job["thread_id"]).answer == "Research is under way."
            )
        finally:
            service.close()
    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver, model=ThinkingDemo())
        try:
            app = Northstar(service)
            app.jobs.clock = lambda: time.time() + 121  # Reclaim the crashed attempt's lease.
            result = app.work(alice, job["id"])
            assert "database operations lead" in result.answer
            assert not service.agent.get_state(service.config(job["thread_id"])).next
            assert app.jobs.get(alice, job["id"])["status"] == "COMPLETED"
        finally:
            service.close()
