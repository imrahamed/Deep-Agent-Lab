"""Build an evidence-aware topic matrix; optional integrations remain explicitly scoped."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPED = {
    "LLM inference": "Mechanics explained; scripted loop verified; one live inference checked",
    "tokens": "Usage accounting verified; actual Ollama token counts recorded in live report",
    "vectors": "Cosine arithmetic verified; live Ollama/OpenSearch retrieval checked",
    "remote MCP": "Real SDK adapter and origin contract verified; remote server not configured",
    "authentication": (
        "Trusted-principal and token-origin contracts verified; OAuth login not implemented"
    ),
    "prompt caching": "Stable-prefix fingerprint verified; provider cache reuse not measured",
    "model judges": (
        "Adapter and calibration verified; measured live labels retained in the live report"
    ),
    "model comparisons": "Controlled trial runner verified; no multi-model quality ranking claimed",
    "cost": "Accounting boundaries explained; prices and local power cost unmeasured",
    "resource analysis": "Measured timings and reported tokens; VRAM and power unmeasured",
    "Langfuse tracing": (
        "Actual SDK and span hierarchy verified locally; external export not verified"
    ),
    "trace privacy": (
        "Content suppression and sanitized exceptions verified; no blanket metadata guarantee"
    ),
    "source revisions": (
        "Provenance and stale-review checks verified; "
        "cross-database fencing remains a design boundary"
    ),
    "active revision hydration": (
        "Stale-ID exclusion and revision propagation verified, including live retrieval"
    ),
}


def main():
    lessons = json.loads((ROOT / "docs/course-manifest.json").read_text(encoding="utf-8"))
    notebooks = json.loads((ROOT / "docs/reports/notebooks.json").read_text(encoding="utf-8"))
    checks = json.loads((ROOT / "docs/reports/checks.json").read_text(encoding="utf-8"))
    passed = {result["notebook"] for result in notebooks["results"] if result["status"] == "passed"}
    all_checks = all(check["returncode"] == 0 for check in checks["checks"])
    rows = []
    for lesson in sorted(lessons, key=lambda item: item["slug"]):
        slug = lesson["slug"]
        notebook = f"notebooks/{slug}/lab.ipynb"
        assert notebook in passed and all_checks and not notebooks["failures"]
        for source in lesson["tests"] + lesson["implementation"]:
            assert (ROOT / source).is_file(), source
        for topic in lesson["topics"]:
            status = SCOPED.get(topic, "Offline implementation and notebook assertions verified")
            rows.append(
                {
                    "module": slug,
                    "topic": topic,
                    "status": status,
                    "documentation": f"docs/modules/{slug}.md",
                    "notebook": notebook,
                    "exercise": f"{notebook}#Exercise",
                    "implementation": lesson["implementation"],
                    "tests": lesson["tests"]
                    + (
                        ["tests/test_citation_repair.py"] if topic == "bounded repair loops" else []
                    ),
                }
            )
    text = """# Course coverage and verification scope

Every row maps a topic to reading, application code, an executed notebook, a
complete exercise solution and automated tests. **Verified** refers to the stated
local contract and lab scope. It does not certify arbitrary live-model behavior,
an OAuth deployment, distributed graph ownership or cross-database atomicity.
Provider-dependent and unavailable measurements are identified explicitly.

All module notebooks were executed top to bottom in fresh project-Python kernels.
The test suite and compatibility checks passed. Evidence is retained in
[checks](reports/checks.json), [notebook executions](reports/notebooks.json),
[measured evaluations](reports/evaluation.json) and [live checks](reports/live.json).
The original walkthrough and the two deep dives are also included in the notebook
execution report. The matrix records tested scope instead of marking optional
external behavior complete.

| Module / topic | Reading | Code | Lab + solution | Tests | Verified scope |
| --- | --- | --- | --- | --- | --- |
"""
    for row in rows:
        sources = "<br>".join(f"[{Path(p).name}](../{p})" for p in row["implementation"])
        tests = "<br>".join(f"[{Path(p).name}](../{p})" for p in row["tests"])
        text += (
            f"| {row['module'][:2]} · {row['topic']} | [Chapter](../{row['documentation']}) | "
            f"{sources} | [Lab](../{row['notebook']}) · [Exercise](../{row['exercise']}) | "
            f"{tests} | {row['status']} |\n"
        )
    text += """

Optional follow-on topics from the reference (agent-to-agent protocols, browser
agents, multimodal retrieval, prompt optimization, advanced asynchronous subagents
and knowledge graphs) are discussed in [advanced topics](advanced-topics.md).
They are not represented as completed integrations. Deployment and PDF ingestion
remain secondary to the thirteen core AI engineering modules.
"""
    (ROOT / "docs/coverage.md").write_text(text, encoding="utf-8")
    (ROOT / "docs/reports/coverage.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Mapped {len(rows)} topics to verified local artifacts and explicit integration scope.")


if __name__ == "__main__":
    main()
