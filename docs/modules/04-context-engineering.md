# Context engineering

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 03](03-evaluation-foundations.md) and the [retrieval baseline](07-agentic-rag.md#retrieval-baseline). Recommended next is [Module 05](05-skills-and-memory.md).

Estimated time 90 minutes. Difficulty intermediate. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_context_memory_planning.py) alongside the source links below.

## Northstar V4 progression

V3 verifies references and records gaps. Long history can lose a precondition or unresolved question. This module adds the capability to preserve structured working state during selection and compaction.

The deterministic acceptance criterion is all durable state fields survive compaction. Live model judgments are recorded independently.

## Context is not memory

An LLM has no automatic persistent access to earlier application events.

For each inference, the application constructs the model-visible input:

$$ C = I + H + T + E + W $$

Where:

- $ I $: instructions
- $ H $: retained conversation history
- $ T $: tool definitions and messages
- $ E $: retrieved evidence
- $ W $: relevant working-state information

These components compete for a finite context budget.

The engineering problem is not simply making the context shorter. It is **keeping the information needed for the next decision while retaining access to the original evidence**.

Imagine an incident investigator's desk. The desk holds the material currently being read. A filing cabinet holds original records. A notebook contains the investigator's current conclusions and open questions.

You would not place every historical incident report on the desk simultaneously.

Similarly, an agent needs a small active context, durable reference material, and structured working state.

## Five context strategies

| Strategy            | Mechanism                                 | Appropriate use              |
| ------------------- | ----------------------------------------- | ---------------------------- |
| Selective retrieval | Include only relevant passages            | Every research question      |
| Offloading          | Store bulky results outside model context | Large search or tool outputs |
| Trimming            | Remove older or redundant messages        | Repetitive exchanges         |
| Summarization       | Condense earlier conversation             | Long-running work            |
| Context isolation   | Use child-agent contexts                  | Independent complex subtasks |

These strategies are complementary.

The repository's context lab already demonstrates offloading a large result and returning a file pointer. Its summarization lab demonstrates a compacted history and retained checkpoint state.

The important extension is to make the preservation policy explicit.

## What a summary must preserve

A poor Northstar summary might say:

> We reviewed recovery procedures and found the responsible teams.

That loses the information necessary to continue safely.

A useful summary should preserve:

```
{
  "objective": "Prepare a SEV-1 recovery readiness brief",
  "confirmed_facts": [
    {
      "fact": "Restore requires Database Operations Lead approval",
      "evidence_id": "BKP-7#p12",
      "revision": "4"
    }
  ],
  "constraints": [
    "Do not infer a shared approval process without evidence"
  ],
  "decisions": [
    "Separate restore authorization from incident coordination"
  ],
  "unresolved_questions": [
    "Does a combined approval procedure exist?"
  ],
  "working_files": [
    "/drafts/recovery-brief.md"
  ]
}
```

This is significantly more useful than a generic narrative summary.

However, the summary is still not the source of truth. Exact quotations, timestamps, revisions, and approval decisions must remain available in their authoritative records.

## Implementation: bounded evidence context

### **Code walkthrough**

The `ContextBudget` object records how the application intends to allocate space. It does not make a model's context window larger.

The `approximate_tokens()` function is a teaching heuristic. Production usage accounting should use the actual provider tokenizer or the provider's reported token counts.

`select_evidence()` reserves required passages, then greedily chooses optional passages by relevance. It is intentionally simple.

In a mature system, selection should also consider source diversity, required evidence IDs, contradictions, authority, recency, and the marginal usefulness of additional passages.

The notebook's offload exercise stores the full set for future inspection. In a multi-tenant application, the path must be generated inside an authorized, scoped workspace rather than accepted directly from model output.

### **Selective rereading**

Once a large file is offloaded, the agent should retrieve only the necessary portion:

This is an educational implementation. In Northstar's real filesystem abstraction, use the permitted file-reading tools rather than arbitrary host paths.

## Prompt caching is not memory

Prompt caching may allow a model provider to reuse computation associated with an unchanged prompt prefix.

It can reduce processing cost or latency when supported and applicable. It does not mean the model independently remembers information between requests.

| Mechanism            | What persists                               |
| -------------------- | ------------------------------------------- |
| Prompt caching       | Reusable provider-side computation          |
| Conversation history | Messages the application retains            |
| Checkpoint           | Saved runtime state                         |
| Working file         | External content accessible through tools   |
| Long-term memory     | Application-managed information across runs |

Cache behavior, minimum eligible sizes, retention, and usage reporting are provider-specific.

Do not build correctness assumptions around a prompt-cache hit.

## Context experiment

Run the same Northstar evaluation cases with four configurations.

| Experiment | Context strategy                             |
| ---------- | -------------------------------------------- |
| C1         | All retrieved passages included              |
| C2         | Top four passages only                       |
| C3         | Selected evidence plus file offloading       |
| C4         | Selected evidence plus structured compaction |

Measure task success, expected-evidence recall, claim support, input-token consumption, and total latency.

The key hypothesis is not that fewer tokens always improve accuracy.

It is that **task-aware context selection can reduce wasted context without losing required evidence**.

A possible outcome is that C2 uses fewer tokens but misses a contradictory source. That would be an unacceptable regression even if its answers become faster.



## Executable implementation

The allowance reserves output and safety headroom before selecting evidence. The UTF-8 length heuristic is diagnostic and is not an Ollama tokenizer. Required evidence is charged before optional passages; budget exhaustion becomes an explicit exception. Real Deep Agents middleware offloads results into virtual storage and summarizes history. Our structured compaction copies source revisions, constraints, decisions and open questions without asking a model to rewrite them. Prompt prefix fingerprints identify stable inputs; actual KV-cache reuse is provider behavior.

A shorter prompt can lose decisive counterevidence. Measure evidence retention separately from latency. Summaries are working aids; original records remain the authority for quotations, policy revisions and approvals.

Application sources: [`context.py`](../../src/deep_agent_lab/context.py), [`labs.py`](../../src/deep_agent_lab/labs.py).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-04), which includes learner mechanisms, framework execution, experiments and assertions.



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](03-evaluation-foundations.md) ? [Next module](05-skills-and-memory.md)

Estimated time 90 minutes. Difficulty intermediate.
