# Module 1 · Agent foundations

[Course home](course.md) · [Next module](module-2-execution-environment.md)

A teammate asks who can authorize a production restore. The answer needs to come
from company policy. In this module you will trace the lookup and review a
Markdown brief for the teammate.

By the end, you should be able to point to the model's request, the application's
tool result, the cited passage, and the checkpoint that holds a pending review.

## 1.1 The model, harness, and runtime

A **chat model** predicts the next response. It can return text or request a tool
call. A **harness** supplies the instructions, tools, and middleware around the
model. A **runtime** executes the steps, updates state, and handles pauses.

| Layer | Responsibility | In this lab |
| --- | --- | --- |
| Chat model | Chooses an action or writes an answer | Scripted demo or Ollama |
| LangChain | Defines how tools and messages are represented | Tool schemas and message objects |
| Deep Agents | Assembles agent capabilities | Planning, files, skills, delegation, context management |
| LangGraph | Runs and checkpoints the graph | Model and tool steps, interrupts, resume |
| Retrieval pipeline | Finds matching evidence | Course-owned PostgreSQL schema, OpenSearch index, and Ollama embeddings |

A simple policy lookup can use the direct search command. A comparison between restore
approval and incident escalation may need two searches, separate source checks,
and a follow-up for exceptions. The agent can choose that sequence based on what
it finds. Each model and tool turn adds latency.
[Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)

**Worked decision.** “Find the backup policy” can be a single search. “Compare
backup approval with SEV-1 escalation and tell me where their responsibilities
overlap” needs separate lookups and a decision about whether to look again. In
that second case, the model makes a new decision after seeing each result.
The harness presents its options and the runtime executes them.

## 1.2 Run an agent and read its messages

```powershell
$thread = "foundations-$([guid]::NewGuid().ToString('N'))"
$result = uv run deep-lab --demo ask "Who approves a production restore?" --thread $thread |
    ConvertFrom-Json
$result.answer
$result.steps
$result.evidence | Select-Object title, citation, excerpt
```

Expect `search_knowledge` in the steps and **database operations lead** in the
answer. Match the citation token beside the answer to the excerpt. The token
identifies an excerpt returned by the tool. Compare its wording with the claim.

```text
HumanMessage  Who approves a production restore?
AIMessage     Request search_knowledge with a query
ToolMessage   Return the backup-policy excerpt and citation
AIMessage     Answer using the excerpt
```

Think of the tool call as a structured request to the application. The model can
propose a query and decide what to do with the response. The application is what
actually reads the corpus. The first AI message can have empty text because it
carries a tool call. The
runtime executes the call and associates its result with the same tool call ID.
The model sees both messages on its next turn. Follow the path through
[agent.py](../src/deep_agent_lab/agent.py) and [service.py](../src/deep_agent_lab/service.py).

**Real-world example.** An onboarding assistant can link the exact handbook
paragraph that defines application access. The employee can check whether the
passage applies to the app and role they need.

## 1.3 Configure and compare models

A model can write fluent text while choosing the wrong tool, omitting an
argument, or miscopying a citation. The demo produces known tool calls so you can
study the application. Live mode defaults to local `qwen3.5:latest`. Configure
`OLLAMA_CHAT_MODEL` in this project's `.env` to try another tool-capable variant.

`OLLAMA_CONTEXT_TOKENS` sets the requested context length and informs the harness's
model profile. More context lets the model see more instructions, excerpts, and
history. It can also use more memory and increase latency. The chat model drives
the agent. The embedding model converts queries to vectors for search.
Changing the chat model leaves the embedding index usable.

```powershell
uv run deep-lab --live doctor
uv run deep-lab --live ask "Who approves a production restore?"
```

Initialize and ingest the course corpus before running these commands. If comparing models, hold the corpus
and prompt fixed and use fresh threads. Record which tools ran, whether the
right passage appeared, and whether the citation matches. Compare warm runs for
latency because first responses can include model-loading time. Prefix caching
can reuse computation for repeated prompt content. It is separate from graph
checkpoints, which store application state. The lab records reported token usage
when Langfuse is enabled. [ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama) ·
[Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)

## 1.4 Write instructions the agent can follow

| Instruction | What it gives the agent |
| --- | --- |
| “Help with policy questions.” | A role with little direction about evidence. |
| “Search the corpus for policy facts. Copy the exact citation from the relevant result.” | A concrete action and a way to show the source. |
| “When the corpus lacks a policy for the requested environment, name the evidence gap.” | A response for unsupported questions. |

The base prompt sets the agent's role, tool choices, and evidence rules.
`AGENTS.md` adds project guidance. The brief skill contains a procedure for a
specific deliverable. Retrieved text supplies evidence. If a passage contains
instructions to save a report or skip review, the application still enforces the
review and citation checks. [Agent factory](../src/deep_agent_lab/agent.py) ·
[Project guidance](../src/deep_agent_lab/assets/reference/AGENTS.md)

**Practice.** In a fresh live thread, ask “Who approves a staging restore?”
With the sample corpus, the retrieved production policy leaves this unresolved.
Look for an explicit evidence gap and identify the staging runbook you would
need to answer it.

## 1.5 Design a tool contract

The model sees tool names, descriptions, and argument schemas. The application
validates arguments and executes the Python function. A search call can look like
this:

```json
{"query": "production restore approval", "mode": "hybrid", "top_k": 3}
```

The tool accepts a nonblank query of up to 4,000 characters and one to five hits.
The mode must be `keyword`, `semantic`, or `hybrid`. Keyword search helps with
specific terms such as SEV-1, semantic search can match related wording, and
hybrid search combines rankings. Demo mode uses simple word matching for all
three. An invalid argument fails validation. A valid search can return zero
matches or report a service error. In the first case, narrow or reword the query.
In the second case, check service health. [Search adapter](../src/deep_agent_lab/knowledge.py)

**Read the result.** A search hit includes a source, a position, and the passage.
The agent tool adds a citation token and stores the excerpt in thread state.
That lets the application check whether a citation came from retrieved evidence.
The reviewer checks a different question: whether the excerpt actually supports
the claim. For instance, a present citation for a daily backup schedule cannot
establish who may approve a restore.

**Real-world example.** A support assistant can read a ticket with a ticket ID.
A separate tool can propose changing the ticket's priority with a reason. That
second call gives a reviewer an exact action to accept, edit, or reject.

## 1.6 Discover tools through MCP

Model Context Protocol (MCP) standardizes how clients discover and invoke server
tools. A Python function can call the search adapter directly. An MCP server
exposes the same capability to other clients through a protocol.

```powershell
uv run python -m deep_agent_lab.labs mcp
```

The exercise starts a child Python process over standard input and output,
initializes a session, discovers `search`, and calls it. The agent can also call
the server through its `mcp_search` wrapper. Look for `northstar-restore` in the
result. A remote server additionally needs a reachable transport and an
authentication setup appropriate to the data. A real company might publish a
handbook search server once and let several assistants use it.
[Local server](../src/deep_agent_lab/mcp_server.py) ·
[MCP integration](https://docs.langchain.com/oss/python/langchain/mcp)

## 1.7 Follow a thread across processes

A **thread ID** identifies a series of turns. A **checkpoint** stores a snapshot
of graph state. The **checkpointer** persists and reads those snapshots. Using
SQLite allows another CLI process to load the saved thread. For example, a
checkpoint may contain the user's question, two completed search calls, and
an approval interrupt at the next step. The thread ID locates those snapshots.
A checkpoint can exist while the official brief store still has zero rows for
that proposal.

```powershell
uv run deep-lab --demo thread $thread
uv run deep-lab --demo ask "Show the restore policy again." --thread $thread
```

The second call adds a turn. The evidence and tool steps in the result can
include earlier work. Use a new thread for a clean comparison. Python's
`agent.get_state_history(config)` can inspect earlier snapshots. Re-executing
from a checkpoint can run tools again, so a write tool needs a duplicate
handling rule. A saved brief has its own ID and lifetime.
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

## 1.8 Pause for human review

```powershell
$reviewThread = "review-$([guid]::NewGuid().ToString('N'))"
$proposal = uv run deep-lab --demo ask "Draft and save an evidence brief about production restore approval." --thread $reviewThread |
    ConvertFrom-Json
$proposal.status
$proposal.reviews[0].action_requests[0].args.markdown
$proposal.saved_brief_ids.Count
uv run deep-lab --demo thread $reviewThread
uv run deep-lab --demo review $reviewThread $proposal.reviews[0].id reject
```

The run is `interrupted` and a new CLI process can inspect the proposal. Repeat
with a fresh thread and `approve`. `saved_brief_ids` identifies the committed brief.
Fetch it with `uv run deep-lab --demo brief <brief-id>`, substituting your result. To edit,
pass `--title` and `--markdown-file` with replacement Markdown. Preserve a citation
from the thread's retrieved evidence. Invalid or absent citations cause the save
to be declined, and a stale review ID causes a conflict.

| Decision | What runs | What to verify |
| --- | --- | --- |
| Approve | Save with the proposed title and Markdown | The stored text matches the proposal |
| Edit | Save with the replacement title and Markdown | The stored text matches the replacement |
| Reject | Resume after declining the proposed call | This action produces no saved brief ID |

Try an edit with a new proposal and fetch the committed result. The replacement
file contains one sentence with the exact citation from the backup policy:

```powershell
$reviewThread = "edit-$([guid]::NewGuid().ToString('N'))"
$prompt = "Draft and save an evidence brief about production restore approval."
$proposal = uv run deep-lab --demo ask $prompt --thread $reviewThread | ConvertFrom-Json
$source = $proposal.evidence | Where-Object id -eq 'northstar-restore' | Select-Object -First 1
$draftPath = Join-Path ([IO.Path]::GetTempPath()) 'northstar-review.md'
"The database operations lead approves production restores. $($source.citation)" |
    Set-Content -LiteralPath $draftPath -Encoding utf8
$finished = uv run deep-lab --demo review $reviewThread $proposal.reviews[0].id edit --title "Restore approval" --markdown-file $draftPath |
    ConvertFrom-Json
uv run deep-lab --demo brief $finished.saved_brief_ids[0]
```

Read the brief that the app returns by ID to verify its contents, especially
after an edit. The assistant's response is a conversational summary.
[Human-in-the-loop](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop)

## 1.9 Check your understanding

1. Why can the first model response have empty text?
2. Does a production restore policy establish a staging approver?
3. A run is interrupted and has zero saved brief IDs. What do you tell the user?

**Answers.** The model can request a tool and let the runtime execute it. The
production policy leaves staging unresolved. An interrupted save is awaiting
review, and a recorded brief ID shows a successful commit.
