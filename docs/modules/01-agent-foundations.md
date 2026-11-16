# Agent foundations

Adapted from the supplied Northstar course reference. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

## LLM inference from first principles

An LLM generates tokens based on a sequence of preceding tokens.

At a simplified level:

$$ P(t_{n+1}\mid t_1,t_2,\ldots,t_n) $$

The model estimates a probability distribution for the next token given the current context.

**Tokens are not the same as words.** A token may represent a word, part of a word, punctuation, or another encoded unit. Different model families use different tokenizers.

The model processes input tokens through a transformer. Attention allows representations at one position to incorporate information from other positions. The model then produces a distribution over possible next tokens.

Token selection can be more or less deterministic depending on decoding settings.

```
Input:
Who approves a production restore?

Candidate next-token continuations:
"The"
"According"
"I"
```

The model does not automatically query Northstar's policy database. Without evidence, a fluent continuation may simply be a plausible guess.

### **Context windows and output limits**

A context window bounds how much tokenized information the model can process in an invocation. It must accommodate model-visible instructions, history, tool schemas, and other supplied content, subject to the provider's exact accounting rules.

Output generation has its own configurable or model-specific limits.

A hypothetical planning budget could be:

```
Available model context:   32,000 tokens
System/tool instructions:   3,000
Conversation and state:     5,000
Retrieved evidence:        12,000
Reserved output:            4,000
Safety headroom:            8,000
```

These numbers are **illustrative**, not Ollama settings or a benchmark.

A large context is not equivalent to persistent memory. Information disappears from the model's current view when an application no longer supplies it. The application must decide what to retain, retrieve, or summarize.

## Model, agent, harness, runtime

These terms describe different responsibilities.

| Component    | What it does                                     | Northstar example                            |
| ------------ | ------------------------------------------------ | -------------------------------------------- |
| Model        | Generates a response or structured action        | Ollama-hosted language model                 |
| Agent        | Uses observations to select subsequent actions   | Search, inspect result, search again, answer |
| Harness      | Supplies instructions, capabilities and policies | Deep Agents                                  |
| Runtime      | Executes, tracks and coordinates operations      | LangGraph                                    |
| Tool         | Performs an action outside inference             | `search_knowledge`                           |
| Checkpointer | Persists execution state                         | SQLite checkpoint backend                    |

An agent is not just a model with a long system prompt.

The essential difference is **the feedback loop**.

The model requests an action. The application actually executes it.

This distinction is essential to debugging, security, and reliability.

## Worked example: one policy question

The model emits a tool request:

```
{
  "id": "call_001",
  "name": "search_knowledge",
  "arguments": {
    "query": "production restore approval",
    "top_k": 3
  }
}
```

The application validates it and searches Northstar.

The result:

```
{
  "call_id": "call_001",
  "status": "success",
  "hits": [
    {
      "id": "BKP-7#p12",
      "revision": "4",
      "excerpt": "Production restores require approval from the Database Operations Lead."
    }
  ]
}
```

The model receives that result and generates:

> The Database Operations Lead must approve a production restore, according to BKP-7 revision 4.

Notice that the tool-call ID establishes which result belongs to which request. This becomes important when an agent issues multiple calls or executes work concurrently.

## Choosing between RAG, workflows, and agents

A direct RAG implementation could simply retrieve relevant documents and call the model once.

A deterministic workflow might perform two specified searches, validate the results, and generate a comparison.

A single agent may decide to reformulate queries after seeing incomplete evidence.

Delegated agents can research independent topics in separate contexts.

| Problem                                            | Preferred starting point |
| -------------------------------------------------- | ------------------------ |
| Find one restore approver                          | Direct RAG               |
| Compare two explicitly named policies              | Deterministic workflow   |
| Discover relevant policies and resolve uncertainty | Bounded single agent     |
| Investigate many independent policy domains        | Consider delegation      |

Agent complexity is justified by uncertainty in the required sequence of work—not by the presence of an LLM.



## Executable implementation

The scripted decision is explicitly a fixture: it performs no neural inference. It still returns the same two kinds of action a live model would request. Pydantic validates at runtime, whereas Python type hints alone do not. The real factory in `agent.py` constructs Deep Agents on LangGraph; its checkpoint contains HumanMessage, AIMessage and ToolMessage objects. The tool-call ID pairs an observation with its request. A workflow fixes the order in code; an agent can select the next tool from observations.

A single policy lookup often needs direct RAG rather than an agent. Use the feedback loop when the next search depends on the previous observation. Temperature zero reduces sampling variation but does not establish factual correctness.

Application sources: [`foundations.py`](../../src/deep_agent_lab/foundations.py), [`agent.py`](../../src/deep_agent_lab/agent.py).

[Open the complete notebook](../../notebooks/01-agent-foundations/lab.ipynb), which includes the implementation from scratch, framework execution, failure experiment, assertions and complete exercise solution.
