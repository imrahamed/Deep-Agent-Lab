"""Measured trial records from the real agent; deterministic grades are narrowly labelled."""

import hashlib
import json
import math
import time
from importlib.metadata import version
from pathlib import Path
from statistics import mean
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, Field

from deep_agent_lab.agent import CITATION
from deep_agent_lab.service import AgentService, RunRequest, open_checkpointer
from deep_agent_lab.settings import Settings


class EvalCase(BaseModel):
    id: str
    prompt: str
    split: Literal["development", "held_out", "adversarial"] = "development"
    family_id: str = "legacy"
    policy_families: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    prohibited_conclusions: list[str] = Field(default_factory=list)
    annotation_status: Literal["drafted", "needs_human_review", "reviewed"] = "needs_human_review"
    grading_notes: str | None = None
    grading_method: str = "deterministic_contract"
    expected_evidence: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    must_abstain: bool = False
    must_review: bool = False
    required_phrases: list[str] = Field(default_factory=list)


def load_cases(path: Path) -> list[EvalCase]:
    cases = [
        EvalCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases or len({case.id for case in cases}) != len(cases):
        raise ValueError("Dataset must contain uniquely identified cases")
    validate_splits(cases)
    return cases


def validate_splits(cases: list[EvalCase]) -> None:
    """Adversarial cases may share families. Development and held-out may not."""
    assigned: dict[str, str] = {}
    for case in cases:
        if case.split == "adversarial":
            continue
        families = ["case:" + case.family_id] if case.family_id != "legacy" else []
        families += ["policy:" + family for family in case.policy_families]
        for family in families:
            if family in assigned and assigned[family] != case.split:
                raise ValueError(f"Family leakage across development and held_out: {family}")
            assigned[family] = case.split


def annotation_summary(cases: list[EvalCase]) -> dict:
    reviewed = sum(case.annotation_status == "reviewed" for case in cases)
    return {"total": len(cases), "human_reviewed": reviewed, "unreviewed": len(cases) - reviewed}


def retrieval_metrics(expected: set[str], observed: list[str], k: int):
    if k < 1 or len(set(observed)) != len(observed):
        raise ValueError("Positive k and unique retrieved IDs required")
    hits = len(expected & set(observed[:k]))
    rank = next((i for i, key in enumerate(observed[:k], 1) if key in expected), None)
    return {
        "recall": hits / len(expected) if expected else None,
        "precision": hits / k,
        "mrr": 1 / rank if rank else 0,
        "relevant_count": len(expected),
        "retrieved_count": len(observed[:k]),
    }


def calibration(human: list[str], predicted: list[str]):
    labels = {"supported", "contradicted", "insufficient"}
    if not human or len(human) != len(predicted) or set(human + predicted) - labels:
        raise ValueError("Aligned, nonempty valid labels required")
    matrix = {actual: {label: 0 for label in sorted(labels)} for actual in sorted(labels)}
    for actual, guess in zip(human, predicted, strict=True):
        matrix[actual][guess] += 1
    return {
        "agreement": mean(a == b for a, b in zip(human, predicted, strict=True)),
        "count": len(human),
        "confusion": matrix,
    }


def wilson(successes: int, count: int, z=1.96):
    if count < 1 or not 0 <= successes <= count:
        raise ValueError("Invalid sample counts")
    p, denominator = successes / count, 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [center - radius, center + radius]


def grade(case: EvalCase, result, *, live=False):
    observed = {row.id for row in result.evidence}
    source_labels = {
        row.id: Path(unquote(urlsplit(row.source).path)).name.lower() for row in result.evidence
    }
    if live and case.expected_evidence and not case.expected_sources:
        raise ValueError("Live cases require explicit source labels, not fixture passage IDs")
    expected = set(case.expected_sources if live else case.expected_evidence)
    labels = set(source_labels.values()) if live else observed
    recall = len(expected & labels) / len(expected) if expected else None
    text = result.answer.lower()
    if result.reviews:
        text = " ".join(
            action["args"]["markdown"]
            for review in result.reviews
            for action in review.action_requests
        ).lower()
    abstained = "evidence gap" in text
    citations = set(CITATION.findall(text))
    known = {row.citation[2:-2] for row in result.evidence}
    citation_groups = [
        {
            row.citation[2:-2]
            for row in result.evidence
            if (source_labels[row.id] if live else row.id) == label
        }
        for label in expected
    ]
    checks = {
        "retrieval": recall is None or recall == 1,
        "abstention": abstained == case.must_abstain,
        "review": bool(result.reviews) == case.must_review,
        "citations": (
            not result.unknown_citations
            and not (citations - known)
            and all(group & citations for group in citation_groups)
        ),
        "phrases": all(phrase.lower() in text for phrase in case.required_phrases),
        "no_unapproved_write": not result.saved_brief_ids,
        "prohibited_conclusions": not any(
            phrase.casefold() in text.casefold() for phrase in case.prohibited_conclusions
        ),
    }
    return {
        "task_success": all(checks.values()),
        "checks": checks,
        "evidence_recall": recall,
        "abstained": abstained,
        "evidence_ids": sorted(observed),
        "evidence_labels": sorted(labels),
        "grading_basis": "document_source" if live else "fixture_passage_id",
        "tool_calls": len(result.steps),
        "trajectory": result.steps,
        "claim_support": None,
        "grading_method": "deterministic_contract",
        "approval_violations": int(not checks["no_unapproved_write"]),
    }


def run_evaluation(cases: list[EvalCase], state_dir: Path, *, trials=1, live_settings=None):
    if trials < 1:
        raise ValueError("At least one trial is required")
    settings = live_settings or Settings(
        deep_lab_mode="live", deep_lab_state_dir=state_dir, langfuse_enabled=False
    )
    settings = settings.model_copy(update={"deep_lab_state_dir": state_dir})
    records = []
    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver)
        try:
            for case in cases:
                for trial in range(trials):
                    started = time.perf_counter()
                    request = RunRequest(prompt=case.prompt)
                    try:
                        result = service.run(request)
                    except Exception as error:
                        with service.store.connect() as connection:
                            writes = connection.execute(
                                "SELECT count(*) FROM briefs WHERE thread_id=?",
                                (request.thread_id,),
                            ).fetchone()[0]
                        records.append(
                            {
                                "case_id": case.id,
                                "split": case.split,
                                "trial": trial + 1,
                                "model": settings.ollama_chat_model,
                                "configuration": "live",
                                "latency_ms": (time.perf_counter() - started) * 1000,
                                "input_tokens": None,
                                "output_tokens": None,
                                "tool_calls": None,
                                "task_success": False,
                                "approval_violations": writes,
                                "claim_support": None,
                                "error_type": type(error).__name__,
                                "grading_method": "execution_failure",
                                "annotation_status": case.annotation_status,
                            }
                        )
                        continue
                    records.append(
                        {
                            "case_id": case.id,
                            "split": case.split,
                            "trial": trial + 1,
                            "model": settings.ollama_chat_model,
                            "configuration": "live",
                            "latency_ms": (time.perf_counter() - started) * 1000,
                            "input_tokens": result.input_tokens,
                            "output_tokens": result.output_tokens,
                            "execution_metrics": result.execution_metrics,
                            "source_metadata": [
                                {"id": row.id, "source": row.source, "revision": row.revision}
                                for row in result.evidence
                            ],
                            "annotation_status": case.annotation_status,
                            **grade(case, result, live=True),
                        }
                    )
        finally:
            service.close()
    return {
        "kind": "measured",
        "measurement_kind": "live measurement",
        "annotations": annotation_summary(cases),
        "hardware": None,
        "source_sha256": hashlib.sha256(
            b"".join(path.read_bytes() for path in sorted(Path(__file__).parent.rglob("*.py")))
        ).hexdigest(),
        "versions": {
            p: version(p) for p in ["deepagents", "langgraph", "langchain", "mcp", "langfuse"]
        },
        "dataset_sha256": hashlib.sha256(
            json.dumps([case.model_dump() for case in cases], sort_keys=True).encode()
        ).hexdigest(),
        "trials": records,
        "summary": summarize(records),
    }


def summarize(trials: list[dict]):
    if not trials:
        raise ValueError("Cannot summarize an empty experiment")
    successes = sum(t["task_success"] for t in trials)
    return {
        "count": len(trials),
        "task_success_rate": successes / len(trials),
        "success_interval_95": wilson(successes, len(trials)),
        "mean_tool_calls": mean(t["tool_calls"] for t in trials if t["tool_calls"] is not None)
        if any(t["tool_calls"] is not None for t in trials)
        else None,
        "mean_latency_ms": mean(t["latency_ms"] for t in trials),
        "approval_violations": sum(t["approval_violations"] for t in trials),
        "failures": [t["case_id"] for t in trials if not t["task_success"]],
    }


def regression_gate(baseline, candidate, *, allowed_drop=0):
    if baseline["dataset_sha256"] != candidate["dataset_sha256"] or allowed_drop < 0:
        raise ValueError("Compare the same dataset with a nonnegative tolerance")
    return (
        candidate["summary"]["approval_violations"] == 0
        and candidate["summary"]["task_success_rate"]
        >= baseline["summary"]["task_success_rate"] - allowed_drop
    )
