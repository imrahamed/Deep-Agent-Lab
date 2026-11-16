# Deep Agent Lab

A project-based AI Agent Engineering course for senior Node.js/TypeScript backend
engineers learning Python. Build one evolving **Northstar Policy Research
Assistant** through thirteen modules: evidence-grounded research, tools and MCP,
context, skills, memory, planning, evaluations, security, human review, durability
and observability.

[Learning path](docs/course.md) | [Notebooks](notebooks/README.md) |
[Architecture](docs/architecture.md) | [Coverage matrix](docs/coverage.md) |
[Verification results](docs/verification.md)

## Start offline

Use Python 3.11 through 3.14 and uv from the repository root:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked --extra dev --extra notebook
uv run deep-lab --demo ask "Who approves a production restore?"
uv run jupyter lab notebooks/01-agent-foundations/lab.ipynb
```

The notebook path is offline by default and creates temporary state. Scripted
models drive real Deep Agents/LangGraph orchestration, MCP, checkpoints and review.
The fictional corpus and observed results are labelled; scripted success does not
establish live-model quality. Explicit `--demo` also disables external tracing.
A pre-existing ignored `.env` may select live mode for commands without that flag.

## Follow the course

| Module | Reading | Standalone notebook |
| --- | --- | --- |
| 01 | [Agent foundations](docs/modules/01-agent-foundations.md) | [Run lab](notebooks/01-agent-foundations/lab.ipynb) |
| 02 | [Tools and MCP](docs/modules/02-tools-and-mcp.md) | [Run lab](notebooks/02-tools-and-mcp/lab.ipynb) |
| 03 | [Evaluation foundations](docs/modules/03-evaluation-foundations.md) | [Run lab](notebooks/03-evaluation-foundations/lab.ipynb) |
| 04 | [Context engineering](docs/modules/04-context-engineering.md) | [Run lab](notebooks/04-context-engineering/lab.ipynb) |
| 05 | [Skills and memory](docs/modules/05-skills-and-memory.md) | [Run lab](notebooks/05-skills-and-memory/lab.ipynb) |
| 06 | [Planning and delegation](docs/modules/06-planning-and-delegation.md) | [Run lab](notebooks/06-planning-and-delegation/lab.ipynb) |
| 07 | [Agentic RAG](docs/modules/07-agentic-rag.md) | [Run lab](notebooks/07-agentic-rag/lab.ipynb) |
| 08 | [Advanced evaluations](docs/modules/08-advanced-evaluations.md) | [Run lab](notebooks/08-advanced-evaluations/lab.ipynb) |
| 09 | [Security and trust boundaries](docs/modules/09-security.md) | [Run lab](notebooks/09-security/lab.ipynb) |
| 10 | [Human review bound to the exact action](docs/modules/10-human-review.md) | [Run lab](notebooks/10-human-review/lab.ipynb) |
| 11 | [Durable execution](docs/modules/11-durable-execution.md) | [Run lab](notebooks/11-durable-execution/lab.ipynb) |
| 12 | [Observability and model comparison](docs/modules/12-observability.md) | [Run lab](notebooks/12-observability/lab.ipynb) |
| 13 | [Integrated Northstar capstone](docs/modules/13-capstone.md) | [Run lab](notebooks/13-capstone/lab.ipynb) |

Each notebook reads like a chapter: problem, objectives, first-principles
explanation, rendered diagram, implementation from scratch, framework execution,
walkthrough, parameter experiments, deliberate failures, assertions, exercises and
complete solutions. Read the [Python bridge](docs/python-bridge.md) if needed.

Complex subjects have additional standalone labs:

- [Claim support, contradictions and abstention](notebooks/07-agentic-rag/evidence-and-claims.ipynb)
- [Separate-process crash and ambiguous-write recovery](notebooks/11-durable-execution/process-recovery.ipynb)

The original [integrated walkthrough](notebooks/deep_agents.ipynb) and legacy
chapters remain available. [Managed deployment](docs/managed-deployment.md) and
[advanced extensions](docs/advanced-topics.md) are optional follow-on material.

## Verify and experiment

```powershell
uv run python scripts/verify_course.py
uv run python scripts/evaluate.py --output docs/reports/evaluation.json
uv run python scripts/check_notebook.py
```

Verification runs lint, the full test suite, locked API compatibility checks,
actual deterministic evaluations and every notebook in a fresh project-Python
kernel. Executed outputs and rendered PNGs are retained. Reports distinguish
measured results from estimates and leave unavailable usage or semantic scores
null. See [verification](docs/verification.md) for scope and limitations.

Reusable application code is in `src/deep_agent_lab/`, reading is in
`docs/modules/`, and the teaching notebooks are edited directly in `notebooks/`.
After changing a notebook, execute it again with `scripts/check_notebook.py`.
The coverage checker uses the curriculum index in `docs/course-manifest.json`.

## Optional live services

Configure your own `.env` using `.env.example`, then opt into live mode. Existing
service configuration is preserved. The course uses its own PostgreSQL schema
`deep_agent_lab` and OpenSearch index `deep-agent-lab-v1`.

```powershell
uv run deep-lab --live doctor
uv run deep-lab --live init
uv run deep-lab --live ingest data/sample
uv run deep-lab --live search "production restore approval" --mode hybrid
uv run deep-lab --live ask "Who approves a production restore? Cite the policy."
uv run python scripts/check_live.py --model --judge
uv run python scripts/evaluate.py --live --trials 3
```

The live verification/evaluation scripts disable external tracing exports. The
application's optional Langfuse integration retains explicit privacy controls;
the course verifies its SDK with a local in-memory exporter. Remote MCP requires
a separately configured trusted HTTPS endpoint and an appropriately scoped token.
[Configuration, API and review commands](docs/operations.md)

The existing FastAPI interface remains a local single-user lab. The integrated
`Northstar` Python boundary adds owned jobs, trusted principal checks, scoped
memory, exact review, fencing and artifact lineage. It expects identity from a
trusted caller; it is not an Internet authentication service. Distributed graph
ownership and cross-database revision fencing need a separate operational design.
[Detailed guarantees](docs/architecture.md)

[Glossary](docs/glossary.md) |
[Primary references and tested versions](docs/references.md)
