# Observability

This chapter develops the Northstar policy research assistant. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 03](03-evaluation-foundations.md) and [Module 11](11-durable-execution.md). Recommended next is [Module 13](13-capstone.md).

Estimated time 90 minutes. Difficulty advanced. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_tracing.py) alongside the source links below.

## Trace structure

A trace represents one logical request or unit of work.

Spans or observations describe its internal operations.

The trace should make it possible to answer:

- Which model configuration was used?
- Which tools were called, with what validated arguments?
- Which evidence IDs were retrieved?
- Which source revisions were considered?
- Where did latency accumulate?
- Was an action approved, edited, rejected, or stale?
- Which saved artifact resulted from the run?

These are observable facts. Debugging should not depend on exposing hidden model reasoning.

## Langfuse instrumentation

Your repository already provides optional Langfuse tracing and privacy controls.

The notebook records actual provider and retrieval operations and invokes the production tracing wrapper. External export can be enabled explicitly with RUN_LANGFUSE_EXPORT=1 and configured Langfuse credentials. Verification keeps export disabled. Automated unit tests check SDK span parentage and exporter failure isolation.

The same instrumentation can be expressed with decorators or manual observations.

The important design is the trace hierarchy, not the specific syntax.

Langfuse's SDKs use OpenTelemetry concepts and support nested observations and evaluation workflows. The repository's declared `langfuse>=5,<6` contract aligns with the Python v5 major.

## Privacy-aware tracing

Avoid storing raw prompts and responses by default when they may contain confidential information.

An informative trace can often use evidence IDs, query hashes, model identifiers, result counts, timings, and error classifications.

```
{
  "run_id": "run-123",
  "thread_id": "thread-456",
  "operation": "hybrid_retrieval",
  "keyword_results": 10,
  "vector_results": 10,
  "final_results": 4,
  "duration_ms": 125,
  "status": "success"
}
```

These values are illustrative.

Also remember that metadata itself can contain sensitive data. Hashing a short or predictable secret is not necessarily sufficient anonymization.

The safest approach depends on organizational data classification, retention, and threat model.

## Diagnosing failure types

A useful diagnostic method follows the execution sequence.

| Symptom                               | Most useful first inspection                 |
| ------------------------------------- | -------------------------------------------- |
| Correct document absent               | Retrieval candidates, index, source revision |
| Correct passage retrieved but omitted | Context selection and truncation             |
| Evidence present but answer false     | Claim generation and support check           |
| Wrong tool chosen                     | Tool schema and model trajectory             |
| Repeated tool calls                   | Agent policy and loop limits                 |
| Save occurred unexpectedly            | Authorization and approval logs              |
| Duplicate brief                       | Idempotency records and write timeline       |
| Slow request                          | Span durations and model/tool resource usage |

This separation prevents you from changing prompts when the problem is actually in the search index.

## Bounded repair loops

A model may produce an answer without citations even though the retrieval result contains good evidence.

Your repository already implements a limited citation-repair mechanism for live mode.

That is a useful pattern if it is bounded and observable.

A general repair policy might be:

```
Generate answer
    ↓
Validate required structure
    ↓
If invalid and repair budget remains:
    provide targeted feedback
    ↓
Regenerate once
    ↓
Validate again
    ↓
Accept or fail safely
```

Avoid unbounded self-criticism loops.

The validator should provide concrete feedback, such as "claim C2 cites an unknown evidence ID," rather than a vague instruction to make the answer better.

## Model selection

Different models can vary in tool-calling reliability, structured output quality, instruction following, latency, context capacity, and resource requirements.

Northstar should evaluate models on its own task distribution.

Do not assume that a model with a larger parameter count is automatically better for every Northstar task.

### **Controlled comparison**

Use the same dataset and, as far as possible, the same retrieval settings, prompts, tool contracts, inference parameters, and hardware conditions.

Record:

| Dimension              | Why it matters                     |
| ---------------------- | ---------------------------------- |
| Task success           | Core usefulness                    |
| Claim support          | Factual reliability                |
| Tool-call correctness  | Agent reliability                  |
| Appropriate abstention | Avoiding unsupported answers       |
| Latency                | User experience                    |
| Context requirements   | Capacity planning                  |
| Peak memory/VRAM       | Local feasibility                  |
| Tokens per second      | Local inference throughput         |
| Hosted API cost        | Operating expense where applicable |

### **Local inference versus hosted pricing**

A hosted API often charges according to input tokens, output tokens, and provider-specific pricing.

Local Ollama inference has different economics.

You may not pay a per-token provider bill, but you still consume CPU/GPU resources, memory, power, and engineering time.

Approximate local operating cost can be modeled as:

$$ C_{\text{local}} = C_{\text{electricity}} + C_{\text{hardware amortization}} + C_{\text{operations}} $$

This is not directly comparable to hosted token prices without accounting for workload, utilization, capacity, and service-level requirements.

No model benchmark or cost claim in this course should be considered measured until an experiment actually produces the corresponding data.



## Executable implementation

The experiment records real model and retrieval durations and provider-reported usage. It prints the production tracing configuration. External export requires its explicit configuration. The application wrapper suppresses input and output content by default and records sanitized exception types. Metadata still needs a deliberate schema because content suppression cannot sanitize arbitrary values. A trace records what happened, while an evaluation judges whether it was correct. Compare models with the same cases, prompts, tool contracts, retrieval and hardware conditions; retain each trial.

Capture only telemetry you can use and retain responsibly. The notebook timeline records actual operations from its kernel. Hosted token prices, power, VRAM and hardware amortization require separate measured inputs; a missing value is not zero.

Application sources: [`tracing.py`](../../src/deep_agent_lab/tracing.py), [`instrumentation.py`](../../src/deep_agent_lab/instrumentation.py), [`storage.py`](../../src/deep_agent_lab/storage.py).

[Open the complete notebook](../../notebooks/12-observability/lab.ipynb), which includes the implementation from scratch, framework execution, failure experiment, assertions and complete exercise solution.


[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](11-durable-execution.md) ? [Next module](13-capstone.md)

Estimated time 90 minutes. Difficulty advanced.

## Executable model comparisons

Run `uv run python scripts/compare.py models --models qwen3.5:latest llama3.2:3b --case-limit 2`
to compare actual configured model executions. The report retains source/dataset hashes,
configuration, parent/child calls, reported usage and a labelled whole-answer support judge.
Draft annotations remain visible and model judgments require calibration. No ranking is
asserted before a corresponding experiment has executed.
