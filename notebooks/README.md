# Master notebook

Open **[deep_agents.ipynb](deep_agents.ipynb)**. It contains all thirteen course topics,
runtime examples, evidence/claim checks and separate-process recovery.

Run the shared setup once, then follow the contents from top to bottom. Each section
allocates its own temporary state; rerun its first code cell and remaining cells to
revisit it. Restart the kernel for a clean full run. Inspect or copy artifacts before
running the final cleanup.

Configure services through [Start here](../docs/start-here.md). Foundations needs Ollama
and local policy files; later sections also need PostgreSQL, OpenSearch and embeddings.
Detailed theory stays in the linked chapters, keeping the notebook focused on code,
experiments and checks. All examples use real implementations and fictional policies.

Run `uv run python scripts/check_notebook.py` to execute the master in a fresh kernel
and export figures. The [course](../docs/course.md) lists chapters and time estimates.
