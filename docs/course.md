# AI Agent Engineering with Northstar

Build one fictional policy research assistant through thirteen modules. Start with a
single lookup, then add evidence verification, context, skills, scoped memory,
planning, security, exact review, durable recovery and measured evaluation.

The audience is a senior Node.js/TypeScript backend engineer learning Python AI
engineering. Python type hints describe structure; Pydantic performs runtime
validation, much like Zod. An async coroutine resembles a Promise, while
asyncio concurrency still needs explicit cancellation and durable ownership.

Open the [master notebook](../notebooks/deep_agents.ipynb) in a fresh kernel and run its
shared setup once. Read the linked concept chapters as needed. Modify
the parameters, reproduce the deliberate failure, attempt the exercise, then run
the complete reference solution. Labs use real models and services, with temporary local state for write exercises.

| Module | Reading | Executable lab | Time | Difficulty |
| --- | --- | --- | --- | --- |
| 01 | [Agent foundations](modules/01-agent-foundations.md) | [Notebook](../notebooks/deep_agents.ipynb#module-01) | 60 min | Introductory |
| 02 | [Tools and MCP](modules/02-tools-and-mcp.md) | [Notebook](../notebooks/deep_agents.ipynb#module-02) | 75 min | Introductory |
| 03 | [Evaluation foundations](modules/03-evaluation-foundations.md) | [Notebook](../notebooks/deep_agents.ipynb#module-03) | 60 min | Intermediate |
| 04 | [Context engineering](modules/04-context-engineering.md) | [Notebook](../notebooks/deep_agents.ipynb#module-04) | 90 min | Intermediate |
| 05 | [Skills and memory](modules/05-skills-and-memory.md) | [Notebook](../notebooks/deep_agents.ipynb#module-05) | 75 min | Intermediate |
| 06 | [Planning and delegation](modules/06-planning-and-delegation.md) | [Notebook](../notebooks/deep_agents.ipynb#module-06) | 120 min | Advanced |
| 07 | [Agentic RAG](modules/07-agentic-rag.md) | [Notebook](../notebooks/deep_agents.ipynb#module-07) | 120 min | Intermediate |
| 08 | [Advanced evaluations](modules/08-advanced-evaluations.md) | [Notebook](../notebooks/deep_agents.ipynb#module-08) | 90 min | Advanced |
| 09 | [Security and trust boundaries](modules/09-security.md) | [Notebook](../notebooks/deep_agents.ipynb#module-09) | 90 min | Advanced |
| 10 | [Human review bound to the exact action](modules/10-human-review.md) | [Notebook](../notebooks/deep_agents.ipynb#module-10) | 120 min | Advanced |
| 11 | [Durable execution](modules/11-durable-execution.md) | [Notebook](../notebooks/deep_agents.ipynb#module-11) | 120 min | Advanced |
| 12 | [Observability and model comparison](modules/12-observability.md) | [Notebook](../notebooks/deep_agents.ipynb#module-12) | 90 min | Advanced |
| 13 | [Integrated Northstar capstone](modules/13-capstone.md) | [Notebook](../notebooks/deep_agents.ipynb#module-13) | 150 min | Advanced |

Focused exercises are integrated into the master notebook:

- [Claim support and contradictory evidence](../notebooks/deep_agents.ipynb#claims)
- [Separate-process crash recovery](../notebooks/deep_agents.ipynb#recovery)

Legacy module documents remain background reading. [Managed deployment](managed-deployment.md)
is an optional architecture exercise after the core course.

[Setup and learning path](../README.md) · [Architecture](architecture.md) ·
[Coverage and verification scope](coverage.md) · [Glossary](glossary.md) ·
[Primary references and compatibility](references.md)

## Recommended progression

Follow the master notebook's contents: 01, 02, 07, 03 through 06, then 08 through 13.
Retrieval comes before evaluation and delegation. [Start here](start-here.md) includes
both shell setups. Each section allocates isolated temporary state; rerun its first
code cell and remaining cells to revisit it. Restart the kernel for a clean full run.

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
