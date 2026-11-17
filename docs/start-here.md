# Start here

This course teaches actual model inference, local tools, PostgreSQL/OpenSearch retrieval,
review storage and durable execution. Unit tests isolate failure conditions with test doubles.
The intended learner is a senior Node.js/TypeScript engineer learning Python AI engineering.

## Prerequisites

Use Python 3.11 or newer within the supported range in pyproject.toml, Git, uv, and an
Ollama server with a chat model supporting tools and structured output. Retrieval modules
also need PostgreSQL, OpenSearch and a compatible embedding model. Read the
[Python bridge](python-bridge.md) for Python types, async code and Pydantic.
Use the locked dependencies and configure your own credentials in the ignored `.env` file.
For an existing checkout, change `DEEP_LAB_MODE=demo` to `DEEP_LAB_MODE=live`.

## PowerShell setup

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --locked --extra dev --extra notebook
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Fill in real endpoints and credentials. Set DEEP_LAB_MODE=live.
uv run deep-lab doctor
uv run deep-lab init
uv run deep-lab ingest data/sample
uv run jupyter lab
```

## Bash setup

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --locked --extra dev --extra notebook
[ -f .env ] || cp .env.example .env
# Fill in real endpoints and credentials. Set DEEP_LAB_MODE=live.
uv run deep-lab doctor
uv run deep-lab init
uv run deep-lab ingest data/sample
uv run jupyter lab
```

Only run `init` and ingestion against the intended lab schema/index. Existing configured
services retain the repository's dedicated names. Module 01 uses the model and local policy
files directly and can be completed before configuring database/search services.

## Learning order

Open [the master notebook](../notebooks/deep_agents.ipynb), run the shared setup once,
and follow its contents: 01, 02, 07, 03 through 06, then 08 through 13. Retrieval comes
before evaluation and delegation. Numbered chapter links open the matching sections.
The [course table](course.md) supplies time, difficulty, reading, source and test links.

## Verification and experiments

```bash
uv run pytest -q
uv run python scripts/verify_course.py
uv run python scripts/compare.py retrieval --case-limit 2
uv run python scripts/compare.py context
uv run python scripts/compare.py models --models qwen3.5:latest llama3.2:3b --case-limit 2
uv run python scripts/compare.py delegation --case-limit 2
```

The full verifier executes notebooks against real configured services. Missing prerequisites
fail clearly. Actual model errors and contract failures remain in reports. Provider usage,
latency and comparison configuration come from executions. Heuristic context estimates have
their own labels. Delegation comparisons require human-reviewed cases and report a prerequisite
skip until such cases exist. All 48 machine-drafted cases need human annotation.

Langfuse and remote MCP need their own configured destinations and authorization. Content
capture remains disabled by default. Inspect [operations](operations.md) and
[architecture](architecture.md) before extending deployment or identity integration.

The master notebook includes all thirteen modules, evidence/claim checks and process
recovery. Legacy unnumbered chapters are archived background material.

[Glossary](glossary.md) ? [References](references.md) ? [Coverage](coverage.md)
