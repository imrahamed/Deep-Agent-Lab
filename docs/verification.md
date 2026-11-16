# Verification results

The complete live course gate failed.

| Check | Actual outcome |
| --- | --- |
| lint | passed |
| compatibility | passed |
| tests | failed |

The retained evaluation has 8 actual trials and 0 failed draft contracts. These failures remain visible. Execution success does not establish answer accuracy.

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
