# Durable execution

Adapted from the supplied Northstar course reference. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

## Checkpoints versus durable jobs

A checkpoint records state from which execution can resume.

Your repository already uses SQLite LangGraph checkpoints and demonstrates that a pending human review can survive recreation of the application service.

However, its asynchronous teaching example uses a process-local thread pool. That is a useful way to demonstrate concurrent work, but a thread pool does not provide durable job ownership.

The two mechanisms solve different problems.

| Mechanism             | Responsibility                                    |
| --------------------- | ------------------------------------------------- |
| LangGraph checkpoint  | Preserve graph execution state                    |
| Persistent job record | Track lifecycle, ownership, deadlines and retries |
| Worker                | Execute or resume tasks                           |
| Lease                 | Temporarily establish which worker owns execution |
| Idempotency key       | Prevent duplicate logical side effects            |
| Application database  | Persist approved business records                 |

A production-oriented design often needs all of them.

## The durable job lifecycle

The application must distinguish "the agent is running" from "the latest HTTP request is still open."

A long-running job should remain identifiable when the requesting client disconnects.

## Persistent job schema

For a focused teaching implementation, SQLite is enough. For multiple distributed workers, PostgreSQL or a dedicated durable workflow service is generally more appropriate.

The important difference from a process-local future is that this record survives worker termination.

## Claiming work safely

Multiple workers must not simply read all `QUEUED` records and start executing them.

They need an atomic claim operation.

### **Code walkthrough**

`BEGIN IMMEDIATE` serializes SQLite write transactions. Two workers using the same database cannot simultaneously acquire the same write transaction.

The lease token identifies the execution attempt.

The lease expiration permits another worker to claim a job if its previous owner disappears.

But lease expiration does **not** prove the previous worker stopped. An old worker may still be running.

That is why later state changes need a conditional check against the current lease token.

This is called *fencing*.

## Fenced completion

If the lease expires and another worker claims the job, the old worker cannot successfully complete the job using its outdated lease token.

For a complete system, lease renewal must use a similar conditional update. Long-running work should periodically check cancellation and deadlines.

A lease only protects operations that actually verify it. An unrelated external API will not automatically honor Northstar's fencing token.

## The exactly-once illusion

Consider an external side effect:

```
1. Worker calls save_brief.
2. Database commits the brief.
3. Worker crashes before recording success.
4. Job restarts.
5. Worker executes save_brief again.
```

The checkpoint may indicate that the save step needs to run again.

Therefore:

**Checkpoints do not guarantee exactly-once external effects.**

A checkpoint and a separate application database do not automatically share one atomic transaction.

The usual engineering approach is to combine at-least-once execution with idempotent effects.

For Northstar, the exact approved action should map to one stable artifact ID.

Retries can then return the existing committed result.

### **Crash scenarios**

| Failure point                       | Possible state                    | Recovery action                             |
| ----------------------------------- | --------------------------------- | ------------------------------------------- |
| Before tool execution               | No side effect                    | Retry                                       |
| During retrieval                    | Unknown read outcome              | Retry bounded read                          |
| Before write commit                 | No committed write                | Retry approved action                       |
| After write commit, before response | Write committed, status uncertain | Reconcile by idempotency key                |
| After checkpoint, before next step  | Checkpoint exists                 | Resume from persisted state                 |
| Worker lease expires                | Previous worker may still run     | Fence stale worker                          |
| Cancellation requested              | Job may be in-flight              | Stop future work and enforce write boundary |

The most important case is the ambiguous write outcome.

It should trigger reconciliation, not an assumption that the operation failed.

## Checkpoints and process restart

The repository's existing restart test is an excellent learning exercise:

1. Start a brief-generation run.
2. Reach the review interrupt.
3. Close the service and checkpoint connection.
4. Recreate them.
5. Resume the same thread with the matching review ID.
6. Confirm the approved brief exists.

The durable job extension adds lifecycle state around that existing behavior.

When restoring a job, the worker inspects both the job record and the graph state.

If the graph is waiting for review, the worker must not restart research from the beginning.

If the graph has completed but the job record is stale, the worker should reconcile the final artifact and update job status.

If the graph is incomplete, it can resume subject to retry and deadline policy.

## Retry policy and cancellation

Not every failure should be retried.

| Failure                    | Retry?                            |
| -------------------------- | --------------------------------- |
| Temporary search timeout   | Yes, within budget                |
| Invalid tool arguments     | Usually no automatic retry        |
| Permission denied          | No                                |
| Missing evidence           | Not indefinitely                  |
| Model output parse error   | Possibly one bounded repair       |
| Write with unknown outcome | Reconcile before retry            |
| Deadline exceeded          | No further work                   |
| User cancellation          | Stop work and prohibit new writes |

A useful retry policy combines maximum attempts, backoff, deadlines, and error classification.

The system must also ensure that cancellation is not simply a prompt saying "please stop."

Before every consequential write, application code should check the current cancellation and authorization state.



## Executable implementation

A checkpoint answers where graph execution stopped. A job answers who owns the work, how many attempts remain and whether it is cancelled. `BEGIN IMMEDIATE` serializes claims in this local SQLite implementation. A lease may expire while the old process is still alive; every protected transition checks the current token, deadline and lease. The capstone stores jobs in the same database as briefs so its commit guard can fence the write within the brief transaction. External services must implement their own idempotency; a checkpoint cannot make an unrelated external write exactly once.

This queue is a local reference implementation. SQLite is not a distributed worker platform, and a fencing token protects only code that checks it. Long model calls need lease heartbeats at safe boundaries; cancellation prevents new commits but cannot undo an already committed effect.

Application sources: [`jobs.py`](../../src/deep_agent_lab/jobs.py), [`storage.py`](../../src/deep_agent_lab/storage.py), [`capstone.py`](../../src/deep_agent_lab/capstone.py).

[Open the complete notebook](../../notebooks/11-durable-execution/lab.ipynb), which includes the implementation from scratch, framework execution, failure experiment, assertions and complete exercise solution.
