# Human review

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 09](09-security.md). Recommended next is [Module 11](11-durable-execution.md).

Estimated time 120 minutes. Difficulty advanced. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_review_jobs_security.py) alongside the source links below.

## Northstar V7 progression

V6 coordinates research. A request to save can change after a reviewer reads it. This module adds the capability to bind approve/edit/reject to the exact payload and version.

The deterministic acceptance criterion is changed, expired and stale actions are rejected by storage. Live model judgments are recorded independently.

## Existing Northstar review flow

Your repository already uses a Deep Agents interrupt on `save_brief`, with approve, edit, and reject decisions.

LangGraph persists state at interruption points so the application can resume the corresponding thread later.

The repository also verifies the current interrupt ID and rejects an already-resolved review request.

These are essential foundations.

This module adds stronger binding between the reviewer decision and the exact authorized payload.

## Exact-action approval

```
{
  "name": "save_brief",
  "arguments": {
    "title": "Recovery Readiness",
    "markdown": "Approved policy findings..."
  }
}
```

The approval should authorize this precise action, not a vague instruction such as "the agent may save a brief."

A cryptographic digest can bind the approval to a canonical representation of the payload and its scope.

This hash is a comparison mechanism. It is not a signature and does not authenticate the reviewer.

The complete approval process also needs authenticated reviewer identity, permission checks, immutable proposal storage, expiration, and an atomic state transition.

## Approval state machine

This design treats editing as creating a revised proposal requiring validation and, where policy requires, fresh approval.

That is stricter than letting any edit inherit the authorization of the original payload.

The server must check the proposed action against current permissions and evidence requirements even if a human has supplied the edited text.

## Transactional approval store

The application implements a focused SQLite review ledger. It uses the same database for review state and saved artifacts so the authorization transition and local write can be committed atomically.

The `action_id` is an idempotency key.

The application records the committed brief ID on the unique `review_actions.id` row in the same SQLite transaction.

### Transaction boundary

`BEGIN IMMEDIATE` obtains a SQLite write transaction before checking and updating the action.

The `SAVED` branch allows a repeated identical request to return the existing result.

A conflicting payload is rejected.

The local brief insert and review-state transition belong to one transaction.

The Northstar wrapper checks trusted caller scope before AgentService validates the current interrupt, payload and evidence revisions. The original loopback API remains a single-user lab. A live PostgreSQL revision check and the SQLite commit do not share a distributed transaction; strict live revision fencing needs an additional design.

The reviewer should not be able to call this function directly using an arbitrary `action_id`.

For a multi-user system, the database operation must also verify the tenant and authorized principal within the trusted service boundary.

## Stale approvals

Suppose the reviewer approves a brief citing BKP-7 revision 4.

Before saving, the corpus activates revision 5.

Your application must decide whether policy revision 4 remains valid for the approved brief.

For a report that claims to describe *current* policy, the safer default is to mark the proposal stale and request renewed review.

The revision check should occur immediately before the commit, using authoritative revision data.

In a distributed system, that final check and the relevant write should be protected against races using appropriate transaction isolation, conditional writes, or version fencing.



## Executable implementation

LangGraph resumes an interrupt with Command; it can reenter node code, so the side effect still needs application idempotency. AgentService records the pending action, source revisions, digest, version and expiry. It rechecks active revisions before authorizing. `save_reviewed` accepts only a matching approved payload and atomically inserts the brief and marks the action saved. An edit is an explicit reviewer approval of a newly validated payload and increments its version. Hashes compare content; they do not authenticate the reviewer. Identity and owner permissions are enforced by the capstone wrapper.

Approval authorizes an action; it does not prove every sentence is correct. The local SQL write and review state share a transaction. Live corpus activation in PostgreSQL is a separate database, so strict distributed revision fencing requires an additional transaction or immutable-snapshot policy; the lab does not claim cross-database atomicity.

Application sources: [`storage.py`](../../src/deep_agent_lab/storage.py), [`service.py`](../../src/deep_agent_lab/service.py).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-10), which includes learner mechanisms, framework execution, experiments and assertions.



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](09-security.md) ? [Next module](11-durable-execution.md)

Estimated time 120 minutes. Difficulty advanced.
