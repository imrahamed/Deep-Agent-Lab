# Northstar notebooks

Follow the [thirteen-module learning path](../docs/course.md). Each numbered folder
contains an independent lab with explanations, a rendered Matplotlib diagram,
implementation, parameter experiments, deliberate failures, assertions and worked
solutions. Modules 07 and 11 include deeper standalone notebooks. The original
`deep_agents.ipynb` walkthrough is retained.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked --extra dev --extra notebook
uv run jupyter lab notebooks/01-agent-foundations/lab.ipynb
uv run python scripts/check_notebook.py
```

The checker starts a fresh kernel for each notebook using the exact project Python,
executes all cells, rejects unexpected errors, checks PNG diagram outputs and saves
the executed notebooks plus `docs/reports/notebooks.json`. Optional live cells use
`RUN_LIVE = False` by default. They are not counted as live-tested by the checker.

Edit the teaching notebooks directly in Jupyter and update the paired reading in
`docs/modules/` when needed. Run the checker again after editing to refresh
execution evidence. The notebooks are self-contained teaching artifacts.
