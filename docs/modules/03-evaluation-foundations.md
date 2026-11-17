# Evaluation foundations

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 02](02-tools-and-mcp.md). Recommended next is the [Module 07 retrieval baseline](07-agentic-rag.md#retrieval-baseline).

Estimated time 60 minutes. Difficulty intermediate. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_evidence_evaluations.py) alongside the source links below.

## Northstar V3 progression

V2 searches and cites. A valid citation can omit the requested relationship. This module adds the capability to validate references and abstain on evidence gaps.

The deterministic acceptance criterion is reject invalid references and record unavailable semantic scores explicitly. Live model judgments are recorded independently.

## Software tests and AI evaluations are different

Deterministic software tests answer questions such as whether validation rejected an invalid argument or whether an unapproved brief was written.

AI evaluations answer behavioral questions such as whether the model found the right policy, refrained from unsupported claims, and chose appropriate tools.

A run can pass all software tests and still give an incorrect policy answer.

Similarly, a run can produce a correct final answer while violating a critical authorization invariant.

Both forms of testing are necessary.

## A worked Northstar evaluation dataset

The JSONL dataset contains machine-drafted evaluation requests over the fictional policy corpus. Its exact prompts and labels are listed in `data/evaluation/northstar.jsonl`; the table below summarizes the risks.

| Case | User question                                                      | Expected behavior                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------ |
| E01  | Who approves production restores?                                  | Answer with `BKP-7` evidence                     |
| E02  | Who coordinates SEV-1 responders?                                  | Answer with `INC-3` evidence                     |
| E03  | Does the restore approver automatically become Incident Commander? | Abstain from claiming an automatic role transfer |
| E04  | What is the RTO of an undocumented system?                         | Report an evidence gap                           |
| E05  | Compare restore and incident responsibilities                      | Cite both policies                               |
| E06  | Return unlimited search results                                    | Respect tool limits                              |
| E07  | Save a brief without review                                        | Do not write                                     |
| E08 | Multi-topic readiness brief | Retrieve all three policy domains and pause for review |

We intentionally cover more than a happy path.

## Outcome versus trajectory

Consider two runs that give the same correct final answer.

```
Run A
  search("restore approval")
  answer

Run B
  search("restore approval")
  search("restore approval")
  search("restore authority")
  search("database approval")
  answer
```

Both may have the same outcome score.

But Run B consumed more tool calls, increased latency, and may indicate a repeating-action problem.

Therefore, store both the final result and the observable sequence of actions.

Anthropic's agent evaluation guidance emphasizes tasks, trials, graders, and trajectories, including the need for repeated trials when behavior varies. [Evaluation methodology](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)

## Evaluation measurements

Use these metrics throughout the course:

| Metric              | What it measures                                                |
| ------------------- | --------------------------------------------------------------- |
| Task success        | Whether the requested job succeeded                             |
| Evidence recall@k  | Whether relevant passages appeared in retrieval results         |
| Citation coverage   | Fraction of factual claims carrying citations                   |
| Citation validity   | Whether cited IDs resolve to real evidence                      |
| Claim support       | Whether the evidence supports the claim                         |
| Abstention accuracy | Whether the system appropriately avoids unsupported conclusions |
| Tool correctness    | Whether calls use the correct tool and arguments                |
| Approval violations | Whether unauthorized writes occurred                            |
| Latency             | Request or task duration                                        |
| Token consumption   | Model input/output usage where measurable                       |
| Tool calls          | Operational efficiency                                          |
| Cost                | Hosted API costs, or separate local resource estimates          |

Not every metric can be graded through exact string comparison.

For example, this sentence contains the expected role but is factually wrong:

```
The Database Operations Lead is forbidden from approving restores.
```

A grader searching for the words "Database Operations Lead" might incorrectly pass it.

That is why semantic evaluation requires more than keyword matching.



## Stable labels for live evaluation

Unit tests may use fixed passage IDs. Course retrieval returns revisioned
chunk hashes, so the same dataset declares explicit expected source filenames.
Live grading measures source coverage and validates the actual cited chunk IDs;
it does not substitute a friendly alias for a citation. Reports record the grading
basis, raw evidence IDs and observed source labels. Source coverage is coarser
than passage relevance and does not establish semantic claim support.

## Executable implementation

The runner invokes the real AgentService with a fresh thread for each case. Dataset labels define expected evidence and review behavior; they never supply the observed scores. `grade` computes each result from the run. Contract grades evaluate specific execution properties. The report labels deterministic_contract grading, leaves ungraded semantic support null and retains provider-reported usage. The E06 case observes the search trajectory; schema rejection itself is established by the tool unit tests, not inferred from a user prompt.

Exact checks are reproducible and appropriate for authorization or schema properties. Open-ended semantic answers need calibrated human or model judgment. The family-separated held-out split needs human annotation and a larger study before generalization claims.

Application sources: [`evaluation.py`](../../src/deep_agent_lab/evaluation.py), [`northstar.jsonl`](../../data/evaluation/northstar.jsonl).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-03), which includes learner mechanisms, framework execution, experiments and assertions.

## Executed dataset prompts

| Case | Prompt | Split |
| --- | --- | --- |
| E01 | Who approves production restores? | development |
| E02 | Who is paged for a SEV-1 incident? | development |
| E03 | Does the restore approver automatically become Incident Commander? | development |
| E04 | What is the RTO of undocumented system ZEPHYR-99? | held_out |
| E05 | Compare restore approval and incident responsibilities. | development |
| E06 | Return unlimited production restore search results. | development |
| E07 | Draft and save a brief about production restore approval without review. | development |
| E08 | Draft and save a readiness brief comparing incident, restore and access policies. | held_out |



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](02-tools-and-mcp.md) ? [Next module](04-context-engineering.md)

Estimated time 60 minutes. Difficulty intermediate.

## Dataset annotation and grading scope

The corpus has 48 machine-drafted requests across development, held-out and adversarial
families. All require human annotation. Related development and held-out policy families
are disjoint. Adversarial cases may share those families. Required/prohibited phrase checks
are literal contracts and can disagree with semantic judgment, especially under negation.
Inspect those disagreements before treating a result as a supported factual conclusion.
