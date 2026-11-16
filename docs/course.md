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
the complete reference solution. Labs use real models and services, with temporary local state for write exercises.

| Module | Reading | Executable lab | Time | Difficulty |
| --- | --- | --- | --- | --- |
| 01 | [Agent foundations](modules/01-agent-foundations.md) | [Notebook](../notebooks/01-agent-foundations/lab.ipynb) | 60 min | Introductory |
| 02 | [Tools and MCP](modules/02-tools-and-mcp.md) | [Notebook](../notebooks/02-tools-and-mcp/lab.ipynb) | 75 min | Introductory |
| 03 | [Evaluation foundations](modules/03-evaluation-foundations.md) | [Notebook](../notebooks/03-evaluation-foundations/lab.ipynb) | 60 min | Intermediate |
| 04 | [Context engineering](modules/04-context-engineering.md) | [Notebook](../notebooks/04-context-engineering/lab.ipynb) | 90 min | Intermediate |
| 05 | [Skills and memory](modules/05-skills-and-memory.md) | [Notebook](../notebooks/05-skills-and-memory/lab.ipynb) | 75 min | Intermediate |
| 06 | [Planning and delegation](modules/06-planning-and-delegation.md) | [Notebook](../notebooks/06-planning-and-delegation/lab.ipynb) | 120 min | Advanced |
| 07 | [Agentic RAG](modules/07-agentic-rag.md) | [Notebook](../notebooks/07-agentic-rag/lab.ipynb) | 120 min | Intermediate |
| 08 | [Advanced evaluations](modules/08-advanced-evaluations.md) | [Notebook](../notebooks/08-advanced-evaluations/lab.ipynb) | 90 min | Advanced |
| 09 | [Security and trust boundaries](modules/09-security.md) | [Notebook](../notebooks/09-security/lab.ipynb) | 90 min | Advanced |
| 10 | [Human review bound to the exact action](modules/10-human-review.md) | [Notebook](../notebooks/10-human-review/lab.ipynb) | 120 min | Advanced |
| 11 | [Durable execution](modules/11-durable-execution.md) | [Notebook](../notebooks/11-durable-execution/lab.ipynb) | 120 min | Advanced |
| 12 | [Observability and model comparison](modules/12-observability.md) | [Notebook](../notebooks/12-observability/lab.ipynb) | 90 min | Advanced |
| 13 | [Integrated Northstar capstone](modules/13-capstone.md) | [Notebook](../notebooks/13-capstone/lab.ipynb) | 150 min | Advanced |

Complex topics have additional standalone labs:

- [Claim support and contradictory evidence](../notebooks/07-agentic-rag/evidence-and-claims.ipynb)
- [Separate-process crash recovery](../notebooks/11-durable-execution/process-recovery.ipynb)

The original [integrated walkthrough](../notebooks/deep_agents.ipynb) and legacy
module documents remain available. [Managed deployment](managed-deployment.md)
is an optional architecture exercise after the core course.

[Setup and learning path](../README.md) · [Architecture](architecture.md) ·
[Coverage and verification scope](coverage.md) · [Glossary](glossary.md) ·
[Primary references and compatibility](references.md)

## Recommended progression

Read 01, 02, 03, the [07 retrieval baseline](modules/07-agentic-rag.md#retrieval-baseline),
04, 05, 06, advanced 07, then 08 through 13. [Start here](start-here.md) includes both shell setups.

| Version | Capability | Remaining limitation |
| --- | --- | --- |
| V1 | Answer from supplied policy text | Cannot discover evidence |
| V2 | Search and cite | Retrieval can be irrelevant or incomplete |
| V3 | Verify references and abstain on gaps | Research strategy is fixed |
| V4 | Faithful reformulation and context management | Long work needs explicit durable state |
| V5 | Skills and scoped preferences/memory | Persistence needs provenance and scope controls |
| V6 | Delegation | Coordination can cost more than it saves |
| V7 | Exact human review and save | Process failures can interrupt completion |
| V8 | Durable recovery, idempotency and lineage | Distributed ownership requires further operational design |

Source and test links for each topic are in the [coverage matrix](coverage.md).
Evaluation annotation status and figure readability are explicit review tasks.
