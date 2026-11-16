"""Read-only live dependency, retrieval, inference and optional judge verification."""

import argparse
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from deep_agent_lab.evaluation import calibration, grade, load_cases
from deep_agent_lab.evidence import Claim, Reference, model_verdict
from deep_agent_lab.knowledge import fixture_search
from deep_agent_lab.model import local_model
from deep_agent_lab.rag.models import SearchRequest
from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.service import AgentService, RunRequest, open_checkpointer
from deep_agent_lab.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("docs/reports/live.json"))
    args = parser.parse_args()
    # Verification must not export corpus content or model telemetry to a third party.
    # Langfuse itself is exercised with an in-memory exporter in the notebook and tests.
    settings = Settings(deep_lab_mode="live", request_timeout_seconds=30, langfuse_enabled=False)
    report = {
        "kind": "measured",
        "live": True,
        "model": settings.ollama_chat_model,
        "remote_mcp": "not_configured",
    }
    with RagService(settings) as rag:
        report["health"] = rag.health(check_tracing=False)
        report["external_tracing"] = "disabled; SDK verified with in-memory exporter"
        if not args.health_only:
            try:
                hits = rag.search(SearchRequest(query="production restore approval", top_k=3))
                report["retrieval"] = {
                    "status": "passed" if hits else "empty",
                    "count": len(hits),
                    "revisions_present": bool(hits) and all(h.revision != "unknown" for h in hits),
                }
            except Exception as error:
                report["retrieval"] = {"status": "failed", "error_type": type(error).__name__}
    if args.model:
        with TemporaryDirectory() as directory:
            settings.deep_lab_state_dir = Path(directory)
            with open_checkpointer(settings) as cp:
                service = AgentService(settings, cp)
                started = time.perf_counter()
                try:
                    result = service.run(
                        RunRequest(
                            prompt="Who approves a production restore? Cite the policy passage."
                        )
                    )
                    report["agent"] = {
                        "status": "passed"
                        if result.evidence and not result.unknown_citations
                        else "failed",
                        "duration_seconds": time.perf_counter() - started,
                        "steps": result.steps,
                        "evidence_count": len(result.evidence),
                        "unknown_citations": result.unknown_citations,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "trace_id": result.trace_id,
                        "saved_brief_ids": result.saved_brief_ids,
                    }
                    root = Path(__file__).resolve().parents[1]
                    case = load_cases(root / "data/evaluation/northstar.jsonl")[0]
                    report["agent"]["dataset_contract"] = grade(case, result, live=True)
                except Exception as error:
                    report["agent"] = {
                        "status": "failed",
                        "error_type": type(error).__name__,
                        "duration_seconds": time.perf_counter() - started,
                    }
                finally:
                    service.close()
    if args.judge:
        root = Path(__file__).resolve().parents[1]
        items = [
            json.loads(line)
            for line in (root / "data/evaluation/calibration.jsonl").read_text().splitlines()
        ]
        registry = {row.id: row for row in fixture_search("restore incident access recovery", 5)}
        model = local_model(settings)
        trials = []
        for item in items:
            row = registry[item["evidence_id"]]
            claim = Claim(
                text=item["claim"],
                references=[
                    Reference(evidence_id=row.id, revision=row.revision, quote=row.excerpt)
                ],
            )
            try:
                verdict = model_verdict(model, claim, registry)
                trials.append(
                    {
                        "human": item["human"],
                        "prediction": verdict.label,
                        "status": "completed",
                        "agrees_with_human": verdict.label == item["human"],
                    }
                )
            except Exception as error:
                trials.append(
                    {
                        "human": item["human"],
                        "prediction": None,
                        "status": "failed",
                        "error_type": type(error).__name__,
                    }
                )
        report["judge_label_source"] = "synthetic_course_reference"
        report["judge_trials"] = trials
        completed = [trial for trial in trials if trial["prediction"]]
        report["judge_calibration"] = (
            calibration([t["human"] for t in completed], [t["prediction"] for t in completed])
            if completed
            else None
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
