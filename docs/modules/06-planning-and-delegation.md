# Planning and delegation

This chapter develops the Northstar policy research assistant. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 05](05-skills-and-memory.md) and the [retrieval baseline](07-agentic-rag.md#retrieval-baseline). Recommended next is [advanced Module 07](07-agentic-rag.md#evidence-sufficiency-and-faithful-reformulation).

Estimated time 120 minutes. Difficulty advanced. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_context_memory_planning.py) alongside the source links below.

## Northstar V6 progression

V5 maintains skills and scoped memory. Independent policy research can duplicate work or omit handoffs. This module adds the capability to coordinate specialists with dependency and evidence acceptance checks.

The deterministic acceptance criterion is dependent tasks wait for verified evidence and failures preserve sibling state. Live model judgments are recorded independently.

## Plans are not evidence of completion

Your repository already demonstrates `write_todos` and specialist delegation.

A todo list is useful for coordination, but its status is not proof that a task succeeded.

```
{
  "task": "Verify emergency access requirements",
  "status": "completed"
}
```

This might indicate only that the model called a tool and marked the item complete.

A stronger plan attaches completion criteria and actual evidence.

```
{
  "task_id": "T3",
  "task": "Verify emergency access requirements",
  "status": "verified",
  "evidence_ids": ["ACC-2#p4"],
  "verification": "Authorized policy revision confirmed"
}
```

The difference is analogous to a job queue reporting "handler executed" versus a domain operation reporting "required database state confirmed."

## Plan the dependency graph

Tasks A, B, and C can be performed independently.

Tasks D and E depend on earlier findings.

The save operation cannot happen before human review.

This dependency ordering should exist outside the model's unverified prose.

## Implement a verifiable plan

This is a simplified research-task model. Not every task requires citation evidence: a formatting task may instead require a validated output artifact. In a general planner, completion criteria should be typed according to the task.

The important design decision is that a completion state cannot be set merely because the model requested it.

## Specialist agents and structured handoffs

Delegation becomes attractive when subtasks require independent investigation or would otherwise pollute the parent's context.

For Northstar, useful specialists include the existing `policy-researcher` and `gap-reviewer`.

A good specialist task is narrow:

> Find the currently applicable production restore approval rule. Return the approving role, an exact supporting excerpt, evidence ID, source revision, and any unresolved uncertainty.

A poor task is:

> Research everything about database operations.

The second task has no clear completion condition and encourages unnecessary browsing or retrieval.

### **Structured handoff**

A parent should not treat a child agent's narrative as authoritative. The parent should validate the returned evidence IDs against the canonical evidence registry and check the support relationship.

### **Parent-child context isolation**

The policy researcher might read twenty passages. The parent does not need all twenty passages in its active context.

Instead, the child can return a compact finding with references, and the parent can selectively retrieve exact passages when necessary.

Delegation therefore performs both task separation and context isolation.

Anthropic's multi-agent research engineering article discusses this pattern, while noting that coordination and evaluation introduce additional complexity.

## Parallel execution and bounded concurrency

Concurrency can improve elapsed time when tasks are independent.

It also increases simultaneous resource usage.

Here is a framework-independent educational dispatcher.

### **Code walkthrough**

`asyncio.Semaphore` limits simultaneous operations.

Think of it as a concurrency limiter around `Promise.all()` in TypeScript.

`asyncio.gather()` waits for all requested tasks here, while each task converts supported failures into a result.

`asyncio.timeout()` applies a per-task timeout. It requests cancellation of an overdue coroutine, but it does not guarantee that blocking external work or remote operations stop immediately.

The dispatcher in `planning.py` also enforces a total deadline, a maximum task count and cancellation cleanup while preserving successful sibling results.

This code demonstrates **parallel execution inside one process**. It is not durable background execution.

A process crash can still lose in-flight tasks.

## When delegation is worse

For the question:

> Who approves a production restore?

A delegated approach might involve a parent model invocation, a child invocation, a child search, and a parent verification step.

A direct RAG approach needs one search and one answer-generation step.

Delegation provides little value in that scenario.

A useful architecture experiment compares the single-agent and delegated designs on the same cases.

Collect task success, claim support, number of retrieved passages, latency, model invocations, and resource consumption.

Do not assume that more agents produce better answers.



## Executable implementation

The task graph has two independent research nodes and a dependent comparison. `complete_task` accepts only evidence present in the trusted registry. A todo label is coordination metadata and is insufficient for verification. The existing Deep Agents lab uses separate child contexts and real task tools; child models execute actual research calls and their handoffs require verification. `asyncio.Semaphore` is comparable to a concurrency limiter around Promise.all. Our dispatcher adds per-task timeouts, a total deadline and cancellation cleanup; it remains process-local.

Delegation can isolate large contexts and shorten independent work. It also adds parent/child model calls and verification. For one short passage, direct RAG is usually the simpler baseline. Async execution alone cannot survive a process crash.

Application sources: [`planning.py`](../../src/deep_agent_lab/planning.py), [`labs.py`](../../src/deep_agent_lab/labs.py).

[Open the complete notebook](../../notebooks/06-planning-and-delegation/lab.ipynb), which includes the implementation from scratch, framework execution, failure experiment, assertions and complete exercise solution.



[Prerequisite retrieval baseline](07-agentic-rag.md#retrieval-baseline) ? [Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](05-skills-and-memory.md) ? [Next module](07-agentic-rag.md)

Estimated time 120 minutes. Difficulty advanced.
