from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deep_agent_lab.api import create_app
from deep_agent_lab.labs import run_lab
from deep_agent_lab.service import (
    AgentService,
    Decision,
    ReviewRequest,
    RunRequest,
    open_checkpointer,
)
from deep_agent_lab.settings import Settings

PROMPT = "Draft and save an evidence brief about production restore approval."


def configuration(directory: Path) -> Settings:
    return Settings(
        _env_file=None, deep_lab_mode="demo", deep_lab_state_dir=directory, langfuse_enabled=False
    )


def test_checkpoint_review_restart(tmp_path):
    settings = configuration(tmp_path)
    with open_checkpointer(settings) as checkpointer:
        service = AgentService(settings, checkpointer)
        pending = service.run(RunRequest(prompt=PROMPT, thread_id="verify"))
        service.close()
    assert pending.status == "interrupted"
    assert {"write_todos", "read_file", "search_knowledge", "save_brief"} <= set(pending.steps)
    assert pending.reviews[0].action_requests[0]["name"] == "save_brief"
    with open_checkpointer(settings) as checkpointer:
        service = AgentService(settings, checkpointer)
        saved = service.resume(
            "verify",
            ReviewRequest(
                interrupt_id=pending.reviews[0].id,
                decisions=[Decision(type="approve")],
            ),
        )
        assert saved.status == "completed"
        assert not saved.unknown_citations
        brief_id = saved.saved_brief_ids[0]
        assert service.store.get(brief_id).thread_id == "verify"
        assert service.inspect("new-thread") is None
        service.close()


@pytest.mark.parametrize("decision", ["reject", "edit", "invalid-edit"])
def test_api_review(decision, tmp_path):
    with TestClient(create_app(configuration(tmp_path))) as client:
        assert client.get("/health").json()["status"] == "ok"
        run = client.post("/api/v1/runs", json={"prompt": PROMPT, "thread_id": "verify"})
        assert run.status_code == 200
        pending = run.json()
        assert pending["status"] == "interrupted"
        assert client.get("/api/v1/threads/verify").json()["status"] == "interrupted"
        assert (
            client.post(
                "/api/v1/runs",
                json={
                    "prompt": "Resume independently.",
                    "thread_id": "verify",
                },
            ).status_code
            == 409
        )
        body = {"interrupt_id": pending["reviews"][0]["id"]}
        propose = {"type": "reject"}
        if decision in {"edit", "invalid-edit"}:
            citation = pending["evidence"][0]["citation"] if decision == "edit" else "[[made-up]]"
            propose = {
                "type": "edit",
                "title": "Edited",
                "markdown": f"Database operations lead approves production restores. {citation}",
            }
        body["decisions"] = [propose]
        result = client.post("/api/v1/threads/verify/review", json=body)
        assert result.status_code == 200
        final = result.json()
        assert final["status"] == "completed"
        if decision == "edit":
            brief_id = final["saved_brief_ids"][0]
            brief = client.get(f"/api/v1/briefs/{brief_id}").json()
            assert brief["title"] == propose["title"]
            assert brief["markdown"] == propose["markdown"]
        else:
            assert "was not saved" in final["answer"]
            assert final["saved_brief_ids"] == []
        assert client.post("/api/v1/threads/verify/review", json=body).status_code == 409


def test_learning_labs():
    assert "northstar-restore" in run_lab("mcp")["results"][0]
    workspace = run_lab("workspace")
    assert "permission denied" in workspace["results"][1]
    assert workspace["state_files"] == ["/draft.md"]
    assert run_lab("shell")["exit_code"] == 0
    assert "90" in run_lab("interpreter")["results"][0]
    assert any(path.startswith("/large_tool_results/") for path in run_lab("context")["files"])
    assert run_lab("summarization")["files"] == ["/conversation_history/summary-lab.md"]
    memory = run_lab("memory")
    assert memory["A"]["files"] == ["/private.md"]
    assert memory["B"]["files"] == []
    delegation = run_lab("delegation")
    assert "database operations lead" in delegation["results"][1]
    assert "incident commander" in delegation["results"][1]
    assert delegation["todos"][0]["status"] == "completed"
    assert run_lab("async")["worker_running"]
