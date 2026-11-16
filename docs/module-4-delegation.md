# Module 4 · Planning and delegation

Archived supplemental chapter. Follow the [current thirteen-module course](course.md) and [service setup](start-here.md) for the maintained learning path.

[Course home](course.md) · [Previous module](module-3-context-management.md) · [Next module](module-5-capstone.md)

Compare production restore approval with SEV-1 escalation. Each topic has its
own policy, terminology, and evidence gaps. A supervisor can assign the two
checks independently and bring their findings together. Use the recorded
plan, tool calls, and cited evidence to verify the combined result.

## 4.1 Plan a task with observable steps

A plan helps a long-running agent track work after several searches or tool calls.
`write_todos` records items and their status. It does not start the work or check
that the work was done. Inspect the actual tool results before trusting a
completed plan.

| Step | Work | Completion evidence |
| --- | --- | --- |
| Find restore policy | Search for authorization and first validation step | Exact passage naming the operations lead |
| Find escalation policy | Search for the trigger, first page, and communication deadline | Exact incident policy passage |
| Check the intersection | Search for a combined procedure | A cited rule or an explicit evidence gap |
| Prepare a brief | Write separate findings and a comparison | Each finding has a matching citation |

```powershell
uv run deep-lab --live ask "Draft a brief about production restore approval and delegate an evidence check."
```

Look for `write_todos`, `task`, and `search_knowledge` in `steps`. The live
model can vary the sequence. A one-excerpt lookup is usually cheaper with a
direct search. Use a plan when the task has several independent deliverables
or a failure in one step changes what should happen next.

For example, the restore and incident lookups can run independently. The
overlap check needs the findings from both, and drafting needs those outcomes.
If the incident lookup fails, keep the restore result, identify what remains
open, and rerun or narrow the failed search before claiming both are covered.

## 4.2 Build a specialist team

A subagent starts with a focused assignment and uses its own model context.
The parent receives its result. This lets a child read several passages while
the parent keeps a short finding and source identifiers.

| Specialist | Good assignment | Output to request |
| --- | --- | --- |
| Policy researcher | Find who approves production restores and quote the sentence | Claim, quote, source, citation |
| Gap reviewer | Determine whether the policies describe joint decision authority | Supporting or conflicting evidence, unresolved question |
| General-purpose | Summarize a single provided passage | Short text with the source preserved |

“Research everything about restores” gives a child an unclear stopping point.
“Find one passage naming the approver and one passage describing the first
verification step” gives it a testable task. The capstone's specialists have
search and harness tools. The parent checks citations with its own search.
The parent's `save_brief` tool is where human review happens.

**Worked handoff.** A researcher returns that the database operations lead must
approve a production restore. Another finds that an on-call engineer must page
the incident commander immediately for SEV-1. Those passages establish
different roles. The parent cannot infer a joint approval procedure from them.
It should search for that procedure or record the missing evidence.
[Agent factory](../src/deep_agent_lab/agent.py) ·
[Deep Agents subagents](https://docs.langchain.com/oss/python/deepagents/subagents)

Try writing a handoff with four pieces: the question, the corpus scope, the
format of the result, and the fallback if the evidence is missing. A child
receiving “Check the Northstar incident policy for the initial page. Return
one sentence, the exact quote, and its source. Say which procedure is missing
if you cannot find it” has a clear stopping point. The supervisor supplies the
handoff, and it verifies support before including the claim.

## 4.3 Dispatch batches dynamically

```powershell
uv run python -m deep_agent_lab.labs delegation
```

The exercise starts with two topics and two configured specialists. QuickJS maps
each topic to a call and waits for the results:

```javascript
const topics = ["restore", "incident"];
const results = await Promise.all(
  topics.map(topic => task({
    subagentType: topic,
    description: "Review " + topic
  }))
);
console.log(JSON.stringify(results));
```

Inspect `results` for both findings and `todos` for the completed task. The
interpreter limits simultaneous child calls to two. The team is configured in
Python. The dynamic part is which tasks are sent and how input data determines
the batch. The parent still waits for the batch in this example. Dispatching several
children at once changes how work is scheduled. A background job changes
when the supervisor can return to the user. Module 5 demonstrates that
lifecycle with a worker.

**Real-world example.** A release assistant reviews ten service runbooks.
Dispatch a checklist review per service, keep concurrency within the model and
search service capacity, and merge missing items into one report. If one child
fails, retain the other findings and identify the missing service explicitly.
For a fixed two-policy comparison, ordinary `task` calls may be sufficient.
[Dynamic subagents](https://docs.langchain.com/oss/python/deepagents/dynamic-subagents)

## Check your understanding

1. What is the difference between marking a step completed and verifying it?
2. What should a child return so the parent can verify a policy claim?
3. What determines the number of calls in the QuickJS example?

**Answers.** A completed plan item records a state. The tool results contain the
evidence that work occurred. A child should provide the claim, exact quote,
source, and citation. The list of topics determines the number of calls and the
configured concurrency controls how many can run at once.
