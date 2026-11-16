# Course notebooks

Open the thirteen numbered module labs in Jupyter and execute top to bottom in a fresh
kernel. Each uses actual models, tools and storage. Configure services through the
[start-here page](../docs/start-here.md). The foundation lab needs Ollama and local policy
files. Retrieval labs also need PostgreSQL, OpenSearch and an embedding model.

The original deep_agents notebook and the claim/recovery deep dives are supplemental.
They use the same real implementations. Automated test doubles are under tests only.
Run `uv run python scripts/check_notebook.py` to execute every notebook and export figures.
The [course](../docs/course.md) gives prerequisite order, timing and difficulty.
