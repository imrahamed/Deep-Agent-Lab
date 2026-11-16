# Verification results

The complete offline quality gate passed with the locked project interpreter.

| Check | Observed result |
| --- | --- |
| Ruff | Passed |
| Automated tests | 44 passed |
| API compatibility | Installed versions match uv.lock; required signatures present |
| Notebook execution | 16 passed in fresh kernels; no unexpected cell errors |
| Rendered figures | 22 PNG outputs retained |
| Deterministic evaluation | 8 actual trials; 0 failed contracts |
| Approval violations in fixture evaluation | 0 |

These are measured software and fixture results, not a broad model-quality score.
Semantic claim support is left null in deterministic trial reports. Estimated
context sizes are labelled estimates; provider-reported live token usage is stored
separately. Small repeated fixture trials do not establish statistical generalization.

Live verification independently reached configured PostgreSQL, OpenSearch, hybrid
retrieval and the Ollama agent. The live judge completed 4 calibration cases; 3 predictions matched the synthetic reference labels.
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
