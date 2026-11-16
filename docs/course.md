# AI Agent Engineering with Northstar

Build one fictional policy research assistant through thirteen modules. Start with a
single lookup, then add evidence verification, context, skills, scoped memory,
planning, security, exact review, durable recovery and measured evaluation.

The audience is a senior Node.js/TypeScript backend engineer learning Python AI
engineering. Python type hints describe structure; Pydantic performs runtime
validation, much like Zod. An async coroutine resembles a Promise, while
asyncio concurrency still needs explicit cancellation and durable ownership.

Read the concept chapter and execute the paired notebook in a fresh kernel. Modify
the parameters, reproduce the deliberate failure, attempt the exercise, then run
the complete reference solution. Every module works offline with temporary state.

| Module | Reading | Executable lab |
| --- | --- | --- |
| 01 | [Agent foundations](modules/01-agent-foundations.md) | [Notebook](../notebooks/01-agent-foundations/lab.ipynb) |
| 02 | [Tools and MCP](modules/02-tools-and-mcp.md) | [Notebook](../notebooks/02-tools-and-mcp/lab.ipynb) |
| 03 | [Evaluation foundations](modules/03-evaluation-foundations.md) | [Notebook](../notebooks/03-evaluation-foundations/lab.ipynb) |
| 04 | [Context engineering](modules/04-context-engineering.md) | [Notebook](../notebooks/04-context-engineering/lab.ipynb) |
| 05 | [Skills and memory](modules/05-skills-and-memory.md) | [Notebook](../notebooks/05-skills-and-memory/lab.ipynb) |
| 06 | [Planning and delegation](modules/06-planning-and-delegation.md) | [Notebook](../notebooks/06-planning-and-delegation/lab.ipynb) |
| 07 | [Agentic RAG](modules/07-agentic-rag.md) | [Notebook](../notebooks/07-agentic-rag/lab.ipynb) |
| 08 | [Advanced evaluations](modules/08-advanced-evaluations.md) | [Notebook](../notebooks/08-advanced-evaluations/lab.ipynb) |
| 09 | [Security and trust boundaries](modules/09-security.md) | [Notebook](../notebooks/09-security/lab.ipynb) |
| 10 | [Human review bound to the exact action](modules/10-human-review.md) | [Notebook](../notebooks/10-human-review/lab.ipynb) |
| 11 | [Durable execution](modules/11-durable-execution.md) | [Notebook](../notebooks/11-durable-execution/lab.ipynb) |
| 12 | [Observability and model comparison](modules/12-observability.md) | [Notebook](../notebooks/12-observability/lab.ipynb) |
| 13 | [Integrated Northstar capstone](modules/13-capstone.md) | [Notebook](../notebooks/13-capstone/lab.ipynb) |

Complex topics have additional standalone labs:

- [Claim support and contradictory evidence](../notebooks/07-agentic-rag/evidence-and-claims.ipynb)
- [Separate-process crash recovery](../notebooks/11-durable-execution/process-recovery.ipynb)

The original [integrated walkthrough](../notebooks/deep_agents.ipynb) and legacy
module documents remain available. [Managed deployment](managed-deployment.md)
is an optional architecture exercise after the core course.

[Setup and learning path](../README.md) · [Architecture](architecture.md) ·
[Coverage and verification scope](coverage.md) · [Glossary](glossary.md) ·
[Primary references and compatibility](references.md)
