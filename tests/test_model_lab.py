from pathlib import Path

import pytest
from langchain.messages import AIMessage

from deep_agent_lab.knowledge import load_policy_evidence, local_search
from deep_agent_lab.model_lab import parse_policy_response
from deep_agent_lab.settings import Settings


@pytest.mark.parametrize(
    ("reply", "status"),
    [
        (
            AIMessage(content='{"answer":"fact","evidence_ids":[],"missing_information":[]}'),
            "valid",
        ),
        (AIMessage(content="{}"), "invalid"),
        (AIMessage(content='{"answer":3,"evidence_ids":[],"missing_information":[]}'), "invalid"),
        (AIMessage(content="declined", additional_kwargs={"refusal": "declined"}), "refused"),
        (
            AIMessage(content='{"answer":', response_metadata={"done_reason": "length"}),
            "incomplete",
        ),
    ],
)
def test_provider_response_validation(reply, status):
    assert parse_policy_response(reply).status == status


def test_local_retrieval_reads_real_files_and_tracks_revisions(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("The database lead approves production restores.")
    first = load_policy_evidence(tmp_path)[0]
    assert local_search(tmp_path, "production restore", 1)[0].id == first.id
    path.write_text("The database lead must approve production restores.")
    second = load_policy_evidence(tmp_path)[0]
    assert first.revision != second.revision and first.id != second.id
    assert Path(path).as_uri() == second.source


def test_application_has_no_demo_fallback():
    with pytest.raises(ValueError):
        Settings(_env_file=None, deep_lab_mode="demo")


def test_runtime_does_not_import_test_doubles():
    import ast

    root = Path(__file__).resolve().parents[1]
    for directory in [root / "src", root / "scripts"]:
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    assert not module.startswith(
                        ("tests", "unittest.mock", "langchain_core.language_models.fake")
                    ), path
