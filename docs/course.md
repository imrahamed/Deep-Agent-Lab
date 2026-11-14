# Deep Agent Lab course

A production restore and a customer-facing outage might happen at the same time.
Who approves the restore? Who gets paged? Does policy explain how the two roles
coordinate? You will build an assistant that answers from the fictional Northstar
policies, flags missing evidence, and proposes a brief for a person to review.

[Setup](../README.md) · [Notebook guide](../notebooks/README.md) ·
[Operations reference](operations.md)

## Start here

Follow the README to install dependencies. Then run these examples from the
project root in PowerShell:

```powershell
uv run deep-lab --demo ask "Who approves a production restore?"
```

Use **demo** to learn tool calls, paths, checkpoints, and review. The scripted
model reacts to specific words, so use the prompts as written. Use
[live mode](../README.md#run-with-live-services) for open-ended questions,
real search rankings, and Langfuse traces. Use a fresh thread to start an
independent experiment. Reuse a thread ID to continue a conversation or review
its pending action. Demo and live have separate state directories.

## Lessons and checkpoints

| Module | What you learn | How to check your work |
| --- | --- | --- |
| [1. Agent foundations](module-1-agent-foundations.md) | Model, harness, tools, MCP, checkpoints, and approval | Match a claim to its passage and reopen a pending review from a second process |
| [2. Execution environment](module-2-execution-environment.md) | File backends, permissions, shell, and interpreter | Predict where a draft goes and which reference write is denied |
| [3. Context management](module-3-context-management.md) | Offloading, summarization, skills, and memory | Find the original text behind a preview and explain why another thread cannot see your draft |
| [4. Delegation](module-4-delegation.md) | Planning, specialist handoffs, and dynamic batches | Verify two child findings and explain what completed plan items tell you |
| [5. Capstone](module-5-capstone.md) | Ingestion, hybrid retrieval, FastAPI, traces, and background work | Retrieve the approved brief and check each claim against its passage |
| [6. Managed deployment](managed-deployment.md) | Runtime, model placement, identity, and durable writes | Sketch how the runtime reaches each service and what happens when approval is retried |

## Final exercise

Draft an incident-readiness brief that names the restore approver, identifies
who the on-call engineer pages during a SEV-1, and states any gap around joint
decision authority. Verify each supported claim against the cited passage.
Edit the proposal if needed, approve it, and fetch the exact Markdown saved.
[Capstone acceptance cases](module-5-capstone.md#acceptance-cases)

The lessons adapt the Academy Python course to Ollama, PostgreSQL, OpenSearch,
FastAPI, SQLite, and Langfuse. [Academy syllabus](https://academy.langchain.com/courses/foundation-introduction-to-deepagents) ·
[Course source](https://github.com/langchain-ai/lca-deepagents/tree/9e1fab37b9bcf4d672bdb6b667755f3f668a3fc8)
