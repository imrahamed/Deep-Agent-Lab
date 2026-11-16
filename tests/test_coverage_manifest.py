import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "coverage_report", Path(__file__).resolve().parents[1] / "scripts/coverage_report.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def topic(tmp_path):
    (tmp_path / "explanation.md").write_text("Explanation")
    (tmp_path / "implementation.py").write_text("def compact():\n    pass\n")
    (tmp_path / "test_contract.py").write_text("def test_compaction():\n    pass\n")
    (tmp_path / "lab.ipynb").write_text(json.dumps({"cells": [{"id": "compaction"}]}))
    return {
        "topic": "structured compaction",
        "explained_in": "explanation.md",
        "implemented_by": ["implementation.py:compact"],
        "exercise_cell": "lab.ipynb#compaction",
        "assertion_or_test": ["test_contract.py::test_compaction"],
        "verification_level": "deterministically_tested",
        "live_experiment": None,
    }


def test_valid_deterministic_topic(topic, tmp_path):
    MODULE.validate_topic(topic, tmp_path)


@pytest.mark.parametrize(
    "updates",
    [
        {"implemented_by": ["missing.py"]},
        {"exercise_cell": "lab.ipynb#missing"},
        {"verification_level": "verified"},
        {"verification_level": "live_measured"},
        {"implemented_by": ["implementation.py:missing"]},
        {"assertion_or_test": ["test_contract.py::test_missing"]},
    ],
)
def test_invalid_topic_evidence(topic, tmp_path, updates):
    with pytest.raises(ValueError):
        MODULE.validate_topic({**topic, **updates}, tmp_path)


def test_live_topic_requires_executed_records(topic, tmp_path):
    path = tmp_path / "live.json"
    path.write_text(
        json.dumps({"measurement_kind": "live measurement", "records": [{"status": "skipped"}]})
    )
    live = {**topic, "verification_level": "live_measured", "live_experiment": "live.json"}
    with pytest.raises(ValueError, match="no executed"):
        MODULE.validate_topic(live, tmp_path)
    path.write_text(
        json.dumps({"measurement_kind": "live measurement", "records": [{"status": "completed"}]})
    )
    MODULE.validate_topic(live, tmp_path)
