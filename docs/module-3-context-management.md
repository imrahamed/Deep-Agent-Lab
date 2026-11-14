# Module 3 · Context management

[Course home](course.md) · [Previous module](module-2-execution-environment.md) · [Next module](module-4-delegation.md)

An incident review might span dozens of searches and several draft revisions.
The model sees a bounded input on each turn. The application can store evidence,
history, and working files separately and send only useful pieces to the model.
The practical question is whether you need verbatim data, a compact account of
earlier decisions, or instructions that apply to future work.

## 3.1 Understand the context budget

The context window includes instructions, tool definitions, retained messages,
and selected evidence. All of them compete for space. A request for five long
passages can crowd out recent decisions in a long thread, even when the user's
question is short.

| Strategy | What changes | When to use it |
| --- | --- | --- |
| Bound retrieval | Give the model fewer or shorter passages | Each search returns more text than the task requires |
| Offload | Store raw output and return a preview and path | One result is too big to include in full |
| Summarize | Condense older messages and retain a recent tail | The whole conversation is growing |
| Load skills on demand | Advertise short descriptions and read full instructions when needed | Many repeatable procedures share one agent |
| Delegate | Give a child its own bounded task and context | Independent evidence checks can run separately |

A summary can lose exact wording, IDs, and uncertainty. Use the original passage
for a quote and preserve important fields in structured state. The parent search
tool records each citation and source in `evidence`, which the save action can
validate independently of the current model input.
[Context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering)

## 3.2 Offload a large tool result

```powershell
uv run python -m deep_agent_lab.labs context
```

The tool produces a 9,400-character mock archive. The exercise lowers the inline
size threshold to make offloading visible with a small text. Compare
`original_chars` with `tool_message`. The message starts with a pointer to
`/large_tool_results/fetch_archive` and includes a preview. In a full run the
agent can use `read_file` with an offset and limit to inspect only the part
it needs. In this exercise the displayed `tool_message` is itself shortened
for inspection, so `original_chars` is the useful comparison for the full
tool output.

**Real-world example.** A support search returns a large batch of historical
tickets. Keep their full contents in a scoped workspace, show a preview, and
retrieve only the lines needed for a specific claim. This reduces prompt volume
while preserving the material for verification.

## 3.3 Summarize a long history

```powershell
uv run python -m deep_agent_lab.labs summarization
```

The exercise sends six pairs of synthetic drill notes and acknowledgments, then
a question. A small reported limit makes compaction happen during the lab.
Look for `/conversation_history/summary-lab.md` in `files`. That is where older
material was offloaded. The lab reports both input and checkpoint message
counts. The checkpoint can still retain messages and summary events even when
later model inputs use a compacted view. A higher checkpoint count can therefore
coexist with a shorter model input.

**Practice.** Reduce the number or length of drill notes in the lab and rerun it.
Observe when the history pointer stops appearing. For a postmortem, a useful
summary preserves the open questions, decisions, and source links. The original
incident timeline still supplies exact timestamps.
[Summarization lab](../src/deep_agent_lab/labs.py)

**Worked example.** Keep “the proposed validation step is still under review”
in a summary. Keep the exact approval wording, citation token, and timestamp
in their source record. A later model turn can use the summary to continue
the project and read the source when it needs to quote or verify a detail.

## 3.4 Add a skill for a repeatable procedure

Read the [evidence brief skill](../src/deep_agent_lab/assets/reference/skills/evidence-brief/SKILL.md).
The YAML frontmatter lists the name and when the skill applies. The body tells
the agent how to work through the task. This is progressive disclosure: the
agent can discover which procedure fits without loading every full procedure
into every request.

```powershell
uv run deep-lab --demo ask "Draft an evidence brief about production restore approval."
```

Look for `read_file` before the brief appears. The procedure tells the agent to
state the question, cite each finding, list gaps, and suggest next steps. The
demo is scripted to show the read. Live mode lets you observe whether a model
chooses the skill for a paraphrased request.

**Real-world example.** A documentation team needs both a technical incident
summary and an executive brief. Each can have its own skill that lists
required sections and references an example. A policy excerpt supplies facts,
while the chosen skill changes how those facts are presented.
[Deep Agents skills](https://docs.langchain.com/oss/python/deepagents/skills)

## 3.5 Decide what deserves memory

| Item | Lifetime | Example |
| --- | --- | --- |
| Prompt and retained messages | Current thread unless explicitly carried forward | The user asks for an extra section |
| State file | Follows its thread and checkpointer in this lab | A working draft in `/draft.md` |
| Project memory | Shared instructions loaded from a configured source | Use short bullets and cite policy |
| Namespaced store | Shared within the configured namespace, with lifetime determined by the store | Instructions for one team |
| Saved brief | Application record written after review | Approved Markdown retrieved by its brief ID |

```powershell
uv run python -m deep_agent_lab.labs memory
```

Threads A and B read `/memory/AGENTS.md` from the same in-memory store namespace.
A writes `/private.md` to its own state. B's listing has no A draft. The store in
this exercise resets when the process ends. The capstone reads shared,
versioned guidance from the packaged `AGENTS.md` and persists thread state to
SQLite. For a multi-user deployment, derive namespaces from authenticated
identity and check that users can only see their own state.
[Deep Agents memory](https://docs.langchain.com/oss/python/deepagents/memory)

### Decide where a new item belongs

Suppose a reviewer asks for a one-page format and corrects a timestamp. Put the
format into the skill if it should apply whenever the same report is requested.
Use project memory if every report should follow it. Keep the timestamp
correction with the incident evidence and current draft, where its scope is
clear. Once the report is approved, fetch the committed document by brief ID.

## Check your understanding

1. Must the entire archive fit in the model input before the agent can use it?
2. Where would you keep the exact quote from a policy?
3. Why can two threads read the same guidance while seeing different drafts?

**Answers.** A preview and pointer let the agent read only what it needs. Keep the
quote in a source excerpt or durable evidence record and cite it. Shared memory
routes to a common namespace or directory, while draft files are stored in the
state of each thread.
