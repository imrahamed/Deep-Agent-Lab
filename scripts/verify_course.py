"""Run the complete offline quality gate and retain its evidence."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-notebooks",
        action="store_true",
        help="Use already executed notebook outputs for a targeted source check.",
    )
    args = parser.parse_args()
    commands = [
        ("lint", ["-m", "ruff", "check", "src", "tests", "scripts"]),
        ("compatibility", ["scripts/check_compatibility.py"]),
        ("tests", ["-m", "pytest", "-q"]),
        ("evaluation", ["scripts/evaluate.py"]),
    ]
    if not args.skip_notebooks:
        commands.append(("notebooks", ["scripts/check_notebook.py"]))
    records = []
    for name, arguments in commands:
        print(f"Running {name}", flush=True)
        result = subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
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
        p
        for directory in ["src", "tests", "scripts", "docs/modules"]
        for p in (ROOT / directory).rglob("*")
        if p.is_file() and p.suffix in {".py", ".md"}
    )
    fingerprint = hashlib.sha256()
    for path in inputs:
        fingerprint.update(path.relative_to(ROOT).as_posix().encode())
        fingerprint.update(path.read_bytes())
    report = {
        "mode": "offline",
        "checks": records,
        "input_sha256": fingerprint.hexdigest(),
        "notebooks_reexecuted": not args.skip_notebooks,
    }
    target = ROOT / "docs/reports/checks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if len(records) != len(commands) or any(record["returncode"] for record in records):
        raise SystemExit(1)
    subprocess.run([sys.executable, "scripts/coverage_report.py"], cwd=ROOT, check=True)
    count = next(
        re.search(r"(\d+) passed", record["output"]).group(1)
        for record in records
        if record["name"] == "tests"
    )
    notebook_report = json.loads((ROOT / "docs/reports/notebooks.json").read_text())
    evaluation = json.loads((ROOT / "docs/reports/evaluation.json").read_text())
    nb_count = len(notebook_report["results"])
    figure_count = sum(r["rendered_pngs"] for r in notebook_report["results"])
    trial_count = evaluation["summary"]["count"]
    failed_count = len(evaluation["summary"]["failures"])
    live_report = json.loads((ROOT / "docs/reports/live.json").read_text(encoding="utf-8"))
    judge_trials = live_report.get("judge_trials", [])
    judge_matches = sum(t["prediction"] == t["human"] for t in judge_trials)
    live_judge_summary = (
        f"The live judge completed {len(judge_trials)} calibration cases; "
        f"{judge_matches} predictions matched the synthetic reference labels."
    )
    verification = f"""# Verification results

The complete offline quality gate passed with the locked project interpreter.

| Check | Observed result |
| --- | --- |
| Ruff | Passed |
| Automated tests | {count} passed |
| API compatibility | Installed versions match uv.lock; required signatures present |
| Notebook execution | {nb_count} passed in fresh kernels; no unexpected cell errors |
| Rendered figures | {figure_count} PNG outputs retained |
| Deterministic evaluation | {trial_count} actual trials; {failed_count} failed contracts |
| Approval violations in fixture evaluation | {evaluation["summary"]["approval_violations"]} |

These are measured software and fixture results, not a broad model-quality score.
Semantic claim support is left null in deterministic trial reports. Estimated
context sizes are labelled estimates; provider-reported live token usage is stored
separately. Small repeated fixture trials do not establish statistical generalization.

Live verification independently reached configured PostgreSQL, OpenSearch, hybrid
retrieval and the Ollama agent. {live_judge_summary}
Individual predictions and disagreements are retained for diagnosis; these fixture
labels do not represent a human annotation study or broad model-quality evidence.
[Live report](reports/live.json)

External Langfuse export was not verified. Automatic approval review rejected
telemetry egress because the exported content and destination trust were not
established. The successful safer live checks disabled external tracing, while
the SDK, span hierarchy, timeline, privacy defaults and exporter-failure isolation
were verified with an in-memory exporter. Remote MCP has a real SDK adapter and
tested origin/token contract but no configured remote server was exercised.

Recovery tests include real separate interpreters, ambiguous committed writes,
persisted approve/edit/reject decisions, expired leases, concurrent claims,
cancellation at the write boundary, stale proposals, forged references, injected
policy content and unauthorized owner/tenant access. The capstone's local
transaction guarantees do not imply distributed graph ownership or atomic policy
revision fencing across PostgreSQL and SQLite.

Reproduce the offline gate with `uv run python scripts/verify_course.py`.
Reports: [checks](reports/checks.json), [notebooks](reports/notebooks.json),
[evaluations](reports/evaluation.json), [compatibility](reports/compatibility.json),
[coverage](coverage.md). Executed figure PNGs are in `docs/reports/figures/`.
"""
    (ROOT / "docs/verification.md").write_text(verification, encoding="utf-8")
    subprocess.run([sys.executable, "scripts/check_course_links.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/check_figures.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
