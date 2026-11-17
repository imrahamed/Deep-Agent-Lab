"""Run source contracts and real-service course notebooks, retaining actual outcomes."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-notebooks",
        action="store_true",
        help="Run a targeted source gate without reexecuting notebooks",
    )
    args = parser.parse_args()
    commands = [
        ("lint", ["-m", "ruff", "check", "src", "tests", "scripts"]),
        ("compatibility", ["scripts/check_compatibility.py"]),
        ("tests", ["-m", "pytest", "-q"]),
        ("coverage", ["scripts/coverage_report.py"]),
        ("links", ["scripts/check_course_links.py"]),
    ]
    if not args.skip_notebooks:
        commands += [
            ("live prerequisites", ["-m", "deep_agent_lab.cli", "--live", "doctor"]),
            ("evaluation", ["scripts/evaluate.py", "--live"]),
            ("notebooks", ["scripts/check_notebook.py"]),
            ("figures", ["scripts/check_figures.py"]),
        ]
    environment = {
        **os.environ,
        "DEEP_LAB_MODE": "live",
        "LANGFUSE_ENABLED": "false",
        "RUN_LANGFUSE_EXPORT": "0",
        "LANGSMITH_TRACING": "false",
        "LANGCHAIN_TRACING_V2": "false",
        "PYTHONUTF8": "1",
    }
    records = []
    for name, arguments in commands:
        print(f"Running {name}", flush=True)
        result = subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        records.append(
            {"name": name, "returncode": result.returncode, "output": result.stdout + result.stderr}
        )
        print(result.stdout, flush=True)
        if result.returncode:
            print(result.stderr, flush=True)
            break
    inputs = sorted(
        path
        for directory in ["src", "tests", "scripts", "docs/modules", "notebooks", "data"]
        for path in (ROOT / directory).rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".jsonl", ".ipynb"}
        and ".ipynb_checkpoints" not in path.parts
    )
    fingerprint = hashlib.sha256()
    for path in inputs:
        fingerprint.update(path.relative_to(ROOT).as_posix().encode())
        fingerprint.update(path.read_bytes())
    passed = len(records) == len(commands) and all(record["returncode"] == 0 for record in records)
    report = {
        "mode": "live" if not args.skip_notebooks else "source contracts",
        "checks": records,
        "input_sha256": fingerprint.hexdigest(),
        "notebooks_reexecuted": not args.skip_notebooks,
        "status": "passed" if passed else "failed",
    }
    target = ROOT / "docs/reports/checks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    text = "# Verification results\n\n"
    scope = "complete live course" if not args.skip_notebooks else "targeted source"
    text += f"The {scope} gate {report['status']}.\n\n"
    text += "| Check | Actual outcome |\n| --- | --- |\n"
    for record in records:
        outcome = "passed" if record["returncode"] == 0 else "failed"
        text += f"| {record['name']} | {outcome} |\n"
    unreviewed = "unknown"
    if (ROOT / "docs/reports/evaluation.json").exists() and not args.skip_notebooks:
        evaluation = json.loads((ROOT / "docs/reports/evaluation.json").read_text(encoding="utf-8"))
        summary = evaluation["summary"]
        text += (
            f"\nThe retained evaluation has {summary['count']} actual trials and "
            f"{len(summary['failures'])} failed draft contracts. These failures remain visible. "
            "Execution success does not establish answer accuracy.\n"
        )
        annotations = evaluation.get("annotations", {})
        unreviewed = annotations.get("unreviewed", "unknown")
    text += f"\nCases awaiting human annotation in that cohort: {unreviewed}.\n"
    text += """
All course models, retrieval and middleware use actual implementations. Unit tests isolate
failure conditions with test doubles located under tests. Model judgments, deterministic
contract grades, heuristic token estimates and provider usage have explicit measurement
semantics. Unavailable values remain null. Human annotation and figure-readability review
are pending until performed by humans.

External tracing exports are disabled in verification. Remote MCP requires a separately
configured trusted endpoint. Local transaction guarantees do not establish distributed graph
ownership or atomic source-revision fencing across PostgreSQL and SQLite.

Reproduce with `uv run python scripts/verify_course.py` after configuring real services.
See [checks](reports/checks.json), [evaluation](reports/evaluation.json),
[notebooks](reports/notebooks.json), [figures](reports/figures.json) and [coverage](coverage.md).
"""
    (ROOT / "docs/verification.md").write_text(text, encoding="utf-8")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
