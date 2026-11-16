"""Run real service/model comparisons and retain configuration and provenance."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from deep_agent_lab.comparisons import (
    agent_comparison,
    comparison_report,
    context_comparison,
    retrieval_comparison,
)
from deep_agent_lab.evaluation import load_cases
from deep_agent_lab.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["retrieval", "context", "models", "delegation"])
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--case-limit", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.case_limit < 1:
        parser.error("case-limit must be positive")
    root = Path(__file__).resolve().parents[1]
    cases = load_cases(root / "data/evaluation/northstar.jsonl")
    if args.kind == "delegation":
        cases = [case for case in cases if case.annotation_status == "reviewed"]
    cases = cases[: args.case_limit]
    settings = Settings(langfuse_enabled=False)
    with TemporaryDirectory() as directory:
        if args.kind == "retrieval":
            records = retrieval_comparison(settings, cases)
        elif args.kind == "context":
            records = context_comparison(root / "data/sample")
        elif not cases:
            records = [{"status": "skipped", "reason": "No human-reviewed cases available"}]
        else:
            records = agent_comparison(
                settings,
                cases,
                Path(directory),
                models=args.models or [settings.ollama_chat_model],
                delegated=args.kind == "delegation",
            )
    report = comparison_report(
        records,
        cases,
        {
            "kind": args.kind,
            "models": args.models,
            "case_limit": args.case_limit,
            "chat_model": settings.ollama_chat_model,
            "embedding_profile": settings.embedding_profile,
            "pipeline_version": settings.pipeline_version,
            "context_tokens": settings.ollama_context_tokens,
            "timeout_seconds": settings.request_timeout_seconds,
        },
    )
    output = args.output or root / f"docs/reports/comparison-{args.kind}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Recorded {len(records)} comparison results in {output}")


if __name__ == "__main__":
    main()
