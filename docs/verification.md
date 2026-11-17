# Verification results

The targeted source gate passed.


The master notebook contains all thirteen topics in one file. Live validation on
17 November 2026 completed Modules 01?12 in a sequential fresh-kernel run. The final
capstone passed separately in a fresh kernel after correcting legacy assertions about
model-selected delegation, baseline evaluation scores and fixture-only source IDs.
Exact approval, saved-content equality, owned artifact lineage, cancellation and rejection
were verified against real services. PostgreSQL, OpenSearch and Ollama were healthy.

A further whole-notebook run after the capstone-only corrections has not been performed.
The retained full-run notebook report includes the earlier failures; it is not a success
record for the final source. See the [current master validation scope](reports/master-notebook-validation.json).

| Check | Actual outcome |
| --- | --- |
| lint | passed |
| compatibility | passed |
| tests | passed |
| coverage | passed |
| links | passed |

Cases awaiting human annotation in that cohort: unknown.

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
