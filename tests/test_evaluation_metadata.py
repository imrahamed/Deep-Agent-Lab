import pytest

from deep_agent_lab.evaluation import EvalCase, annotation_summary, grade, validate_splits
from deep_agent_lab.service import RunResult


def test_family_leakage_and_adversarial_exception():
    development = EvalCase(
        id="dev", prompt="question", family_id="same", policy_families=["backup"]
    )
    held_out = development.model_copy(update={"id": "held", "split": "held_out"})
    with pytest.raises(ValueError, match="leakage"):
        validate_splits([development, held_out])
    validate_splits([development, held_out.model_copy(update={"split": "adversarial"})])
    with pytest.raises(ValueError, match="leakage"):
        validate_splits([development, held_out.model_copy(update={"family_id": "different"})])


def test_annotation_defaults_and_prohibited_conclusions():
    case = EvalCase(id="draft", prompt="question", prohibited_conclusions=["No approval required"])
    assert annotation_summary([case]) == {"total": 1, "human_reviewed": 0, "unreviewed": 1}
    result = RunResult(thread_id="test", status="completed", answer="NO APPROVAL REQUIRED")
    assert not grade(case, result)["checks"]["prohibited_conclusions"]
