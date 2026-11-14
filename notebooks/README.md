# Deep Agent Lab notebook

Follow a question from its first search call through a checkpointed brief
review. The [course map](../docs/course.md) has the written lessons and
worked examples.

## Open the lab

From the project root in PowerShell:

```powershell
uv sync --locked --extra notebook
uv run --extra notebook jupyter lab notebooks/deep_agents.ipynb
```

Choose the project environment's Python kernel and run the cells in order.
The offline exercises create temporary checkpoints and use bundled evidence.
Look for a matching citation, a denied write to a reference path, two
specialist results, and a brief ID after approval.

## Try live retrieval

Initialize, check, and ingest the course corpus from the project root:

```powershell
uv run deep-lab init
uv run deep-lab doctor
uv run deep-lab ingest data/sample
```

Set `RUN_LIVE = True` in the final cell and run it. That cell reads the project's
`.env`, uses Ollama and the course's PostgreSQL and OpenSearch resources, and
stores the new thread under the configured live state directory. Compare the
evidence, citations, and tool choices with the scripted result.
[Live configuration](../docs/operations.md#configuration)

## Verify without opening Jupyter

Keep `RUN_LIVE = False` and run:

```powershell
uv run --extra notebook python scripts/check_notebook.py
```

The script executes the offline code cells and checks their assertions.
