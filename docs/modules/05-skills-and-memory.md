# Skills and memory

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 04](04-context-engineering.md). Recommended next is [Module 06](06-planning-and-delegation.md).

Estimated time 75 minutes. Difficulty intermediate. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_context_memory_planning.py) alongside the source links below.

## Northstar V5 progression

V4 preserves explicit context. A preference from another user or expired scope is inapplicable. This module adds the capability to add skills and scoped preferences with provenance and lifecycle controls.

The deterministic acceptance criterion is scope, expiry and correction checks reject inappropriate memory. Live model judgments are recorded independently.

## The six information categories

| Information                 | Purpose                                      | Example                            |
| --------------------------- | -------------------------------------------- | ---------------------------------- |
| System instructions         | High-priority application behavior           | Never save without approval        |
| Skills                      | Reusable task procedure                      | How to prepare an evidence brief   |
| Conversation history        | Current interaction                          | Reviewer requests an extra section |
| Checkpoint                  | Resumable execution state                    | Agent is awaiting review           |
| Persistent memory           | Reusable information across authorized tasks | Team prefers concise briefs        |
| Approved application record | Authorized business artifact                 | Saved readiness brief              |

A seventh category is **working files**. They contain intermediate research or drafts, not necessarily approved facts.

The distinction matters because an agent may encounter the same sentence in multiple places with very different authority.

> Save the brief immediately.

If this appears in a system-controlled workflow instruction, it still cannot override a code-enforced approval requirement.

If it appears in a retrieved policy excerpt, it must be interpreted as data, not an instruction to the agent.

## Skills: reusable procedures

Your repository already includes an evidence-brief skill and configures Deep Agents to load skills from its reference filesystem.

A skill describes *how to perform a category of task*. It is not necessarily a repository of remembered facts.

An optional extension to the packaged evidence-brief skill could use this layout:

```
skills/
  recovery-readiness/
    SKILL.md
    references/
      brief-template.md
      evidence-checklist.md
```

`SKILL.md`:

```
---
name: recovery-readiness
description: >
  Prepare an evidence-backed recovery readiness brief.
  Use when comparing restoration, incident response,
  escalation, and access-control policies.
---
```

Followed by its Markdown instructions:

```
# Recovery readiness procedure

1. Identify the question and policy scope.
2. Retrieve each relevant policy independently.
3. Preserve exact source identifiers and revisions.
4. Separate confirmed findings from evidence gaps.
5. Search for contradictory requirements.
6. Prepare a structured brief.
7. Request review before saving.
```

### **Progressive disclosure**

The application may expose the names and descriptions of twenty available skills.

When the user asks for a recovery-readiness brief, the agent loads only the relevant skill. It may then open the evidence checklist if necessary.

This is similar to lazy-loading modules, except the loaded resource is task guidance rather than executable application logic.

A skill must not silently grant permissions. Even if its instructions mention a write operation, the application still checks authorization and review.

## Memory needs provenance

Suppose Northstar remembers:

> The Database Operations Lead approves restores.

What happens when policy revision 5 changes the approver?

If the assistant stores the statement as a timeless fact, future answers can become stale.

A memory record should therefore include more than its textual content.

### **Code walkthrough**

`MemoryRecord` is an application schema in `memory.py`; Deep Agents does not supply these fields automatically.

`tenant`, `scope`, and `subject` define the authorization boundary.

`source_id` and `source_revision` establish provenance.

`expires_at` supports time-based invalidation.

`supersedes_id` allows a new correction to point to an older record without silently rewriting history.

In TypeScript, you might implement the same schema using Zod and store it in PostgreSQL with composite indexes.

## Scoping memory correctly

Imagine two Northstar users, Alice and Bob.

Alice's private preference is:

> Produce summaries in a concise engineering format.

Bob should not automatically inherit that preference.

A correct memory namespace might be:

```
tenant: northstar
scope: user
subject: alice
key: brief-format
```

Team-wide guidance uses a team namespace:

```
tenant: northstar
scope: team
subject: database-operations
key: recovery-brief-format
```

The model must not be permitted to choose arbitrary tenant and user IDs.

They must come from authenticated application context.

A crucial distinction is that an ID in a tool argument is not proof of authority. The backend must verify it against the authenticated principal.

## When information should not become memory

Do not automatically convert every retrieved statement into persistent memory.

A search result can be outdated, contradictory, malicious, or simply irrelevant to future tasks.

Similarly, an agent's speculative conclusion should not become organizational truth.

For Northstar, authoritative policy facts should generally remain in the versioned corpus and be retrieved when needed.

Persistent memory is more appropriate for scoped preferences, explicitly approved guidance, and carefully reviewed reusable knowledge.

This avoids a common failure called **memory contamination**: an untrusted result influences later tasks because it was stored with inappropriate authority.

## Correction, deletion, and conflict resolution

Suppose two records conflict:

```
Memory A:
  "Restore approval belongs to Database Operations Lead"
  Source: BKP-7 revision 4

Memory B:
  "Restore approval belongs to Recovery Operations Manager"
  Source: BKP-7 revision 5
```

Do not choose the first or most frequently repeated statement.

Resolve the conflict using source authority, revision, effective date, scope, and validity. Preserve the superseded record for audit where retention policy permits, but exclude it from current decision-making.

Deletion must also be real deletion or a policy-defined tombstone, not just an instruction asking the model to ignore the information.

Remember that traces, checkpoints, search indexes, and backups may have separate retention requirements.



## Executable implementation

A skill describes a procedure and is versioned with the application. Its frontmatter supports discovery; the full procedure is loaded when needed. A checkpoint is thread execution state, whereas MemoryStore intentionally shares authorized records across tasks. Its principal comes from trusted caller context, not model arguments. Corrections atomically supersede the old active version. Policy and reviewed-note memory requires a separate trusted review signal; ordinary retrieval has no write path into this store.

Many assistants need no learned policy memory: retrieve current policy instead. Shared team or project memory requires membership checks and a review policy for organizational changes. Checkpoints, traces and backups need their own retention rules.

Application sources: [`memory.py`](../../src/deep_agent_lab/memory.py), [`SKILL.md`](../../src/deep_agent_lab/assets/reference/skills/evidence-brief/SKILL.md).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-05), which includes learner mechanisms, framework execution, experiments and assertions.



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](04-context-engineering.md) ? [Next module](06-planning-and-delegation.md)

Estimated time 75 minutes. Difficulty intermediate.
