# Agentic RAG

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 03](03-evaluation-foundations.md) for the baseline and [Module 04](04-context-engineering.md) for adaptive research. Recommended next is [Module 04](04-context-engineering.md) after the baseline, then [Module 08](08-advanced-evaluations.md) after adaptive research.

Estimated time 120 minutes. Difficulty intermediate. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_evidence_evaluations.py) alongside the source links below.

## Northstar V4 progression

V3 validates references and recognizes missing evidence. A terminology mismatch blocks an otherwise answerable lookup. This module adds the capability to reformulate faithfully against the original question.

The deterministic acceptance criterion is budget and identifier checks constrain every executed rewrite. Live model judgments are recorded independently.

## Existing Northstar retrieval architecture

Your repository already implements a meaningful hybrid retrieval pipeline.

The actual repository also validates embedding profiles and handles revision cleanup.

This is worth understanding before adding an "agentic" layer.

## BM25: lexical relevance

BM25 is a ranking function designed around term matching, term frequency, document frequency, and document length.

A common BM25 formulation is:

$$ \operatorname{BM25}(q,d) = \sum_{t\in q} \operatorname{IDF}(t) \frac{f(t,d)(k_1+1)} {f(t,d)+k_1(1-b+b|d|/\overline{|d|})} $$

Here:

- $ f(t,d) $ is the frequency of term $ t $ in document $ d $.
- $ |d| $ is document length.
- $ \overline{|d|} $ is average document length.
- $ \operatorname{IDF}(t) $ reflects term rarity.
- $ k_1 $ controls term-frequency saturation.
- $ b $ controls document-length normalization.

The exact IDF variant and search behavior depend on the engine.

### **Why term rarity matters**

Suppose the user searches:

> SEV-1 incident commander

The term "incident" may appear throughout the corpus.

"SEV-1" and "commander" may be more discriminative.

BM25 accounts for that distinction.

It is particularly useful for exact policy names, identifiers, unusual terminology, and specific error codes.

Production Northstar delegates BM25 to OpenSearch. The notebook reimplements it to expose the ranking arithmetic.

The purpose of learning the formula is understanding why a keyword result ranks highly or poorly.

## Vector retrieval: semantic similarity

An embedding model transforms text into a numerical vector:

$$ f(\text{text}) \rightarrow \mathbf{v}\in\mathbb{R}^d $$

A query and document passage are embedded into a comparable vector space.

A common similarity measure is cosine similarity:

$$ \operatorname{cosine}(a,b) = \frac{a\cdot b} {\\|a\\|\\|b\\|} $$

```
Query:
Who coordinates responders during a major outage?

Document:
The Incident Commander coordinates SEV-1 responders.
```

The wording is different, but vector retrieval may recognize semantic similarity.

### **Limitations**

Vector similarity is not proof of factual relevance.

A passage about restore authorization may be semantically close to a question about incident command without answering it.

Vectors also depend on the embedding model, preprocessing, and indexing configuration. Changing models without rebuilding the index can invalidate the meaning of existing vectors even when dimensions match.

Northstar already accounts for embedding-profile compatibility.

## Reciprocal rank fusion

BM25 and vector scores generally occupy different scales.

Combining raw scores directly can therefore be misleading.

Reciprocal rank fusion (RRF) combines rankings instead:

$$ \operatorname{RRF}(d) = \sum_{r \in R} \frac{1}{k+\operatorname{rank}_r(d)} $$

The repository uses `k=60`.

Suppose:

| Document | BM25 rank | Vector rank |
| -------- | --------- | ----------- |
| A        | 1         | 3           |
| B        | 2         | 1           |
| C        | 3         | 2           |

The combined scores are:

$$ A=\frac{1}{61}+\frac{1}{63} $$

$$ B=\frac{1}{62}+\frac{1}{61} $$

$$ C=\frac{1}{63}+\frac{1}{62} $$

RRF rewards documents that appear prominently across retrieval methods.

The `seen` set prevents one retrieval list from counting duplicate IDs repeatedly.

The result is a ranked list, not a statement that any document supports a particular conclusion.

## Agentic retrieval: retrieve according to uncertainty

Direct RAG generally performs a predetermined retrieval operation.

Agentic retrieval allows subsequent retrieval steps to depend on intermediate findings.

Northstar begins with:

> Compare restore and incident approval responsibilities.

A useful bounded sequence is:

```
1. Search restore authorization.
2. Search incident coordination.
3. Identify the unresolved intersection.
4. Search specifically for joint approval or role transfer.
5. Stop if sufficient evidence is found,
   or report the unresolved question.
```

The agent should not search indefinitely.

### **Query decomposition**

A broad question can be decomposed into narrower evidence requirements.

```
questions = [    "Who approves production restoration?",    "Who coordinates SEV-1 response?",    "Does any current policy assign joint authority?",]
```

This improves observability because every subquestion has an expected evidence category.

### **Bounded query reformulation**

A retrieval policy might allow one targeted reformulation after an empty result, then require abstention or escalation.

The model should not repeatedly issue semantically identical queries merely because no answer was found.

### **Optional reranking**

A reranker examines a smaller candidate set and estimates query-document relevance more directly.

A typical pipeline is:

```
BM25 + vector retrieval
        ↓
RRF top 20
        ↓
Optional reranker
        ↓
Top 5 evidence passages
        ↓
Claim verification
```

Reranking can improve selection but adds latency, model dependencies, and another component to evaluate.

For Northstar's small fictional corpus, hybrid retrieval may already be sufficient.

## Structured claims

Instead of treating the entire answer as one unverifiable string, represent factual findings as separate claims.

A supported example:

```
{
  "text": "The database operations lead approves production restores.",
  "references": [
    {
      "evidence_id": "northstar-restore",
      "revision": "4",
      "quote": "The database operations lead approves production restores."
    }
  ]
}
```

An unsupported example:

```
{
  "text": "The Database Operations Lead automatically becomes Incident Commander.",
  "references": [
    {
      "evidence_id": "northstar-restore",
      "revision": "4",
      "quote": "The database operations lead approves production restores."
    }
  ]
}
```

The second reference resolves to a real bundled passage. Its content does not establish the claim. Support is a separate Verdict, rather than a self-declared property of the Claim record.

These human-readable aliases identify the fictional policy sources. The existing repository generates bracketed citation tokens derived from evidence IDs, such as `[[<12-character-hash>]]`. In an actual integration, resolve those exact tokens back to the corresponding stored evidence records rather than relying on a human-readable alias.

## Three levels of citation correctness

| Check             | Question                                                   |
| ----------------- | ---------------------------------------------------------- |
| Citation validity | Does the citation resolve to a real evidence record?       |
| Citation coverage | Does every factual claim have an appropriate citation?     |
| Claim support     | Does the referenced evidence actually establish the claim? |

These properties are independent.

An answer could have 100% citation coverage and still contain unsupported claims.

The save tool validates citation membership. `evidence.py` adds revision and exact-quote checks, a conservative complete-sentence verifier, and an optional model-judge adapter. Human review remains responsible for arbitrary semantic claims in a proposed brief.

## Deterministic evidence validation

Start by checking properties that do not require a language model.

This code verifies provenance and excerpt fidelity.

It does **not** verify semantic entailment.

```
Claim:
"Restore approval is not required."

Evidence:
"Restore approval is required."
```

The source and quotation may both be valid, while the claim contradicts the evidence.

Semantic support can be assessed using a carefully constrained model judge, human review, or task-specific logic. No single method is infallible.

## Missing, contradictory, and stale evidence

Northstar must distinguish three cases.

**Missing evidence:** No retrieved policy establishes the required fact. The assistant should explain what remains unknown and what source is needed.

**Contradictory evidence:** Two applicable sources make incompatible statements. The assistant should preserve both, compare scope and effective dates, and avoid choosing arbitrarily.

**Stale evidence:** A source revision has been superseded. A valid citation to an old revision is not necessarily valid evidence of the current rule.

A useful answer could be:

> BKP-7 revision 4 assigns restore approval to the Database Operations Lead. INC-3 revision 8 assigns incident coordination to the Incident Commander. Neither excerpt establishes automatic transfer of authority between those roles. A joint approval procedure remains an evidence gap.

This is more useful than inventing a convenient relationship.



## Executable implementation

BM25 weights rare terms and saturates term frequency while normalizing document length. Cosine compares direction in one embedding space. RRF uses rank positions because BM25 and vector scores have different scales. Learned vectors come from actual Ollama embedding calls in the service experiments. The existing pipeline hydrates candidate IDs from canonical SQL, excluding orphaned or inactive index records. A reranker scores query/passage relevance; it does not establish claim entailment.

More candidates or reranking can improve recall at additional latency. An empty successful search permits a bounded reformulation; a failed backend must be reported as unavailable. Source changes require rechecking active revisions. The master notebook's evidence subsection examines provenance, conflict and semantic limits in depth.

Application sources: [`retrieval.py`](../../src/deep_agent_lab/retrieval.py), [`evidence.py`](../../src/deep_agent_lab/evidence.py), [`pipeline.py`](../../src/deep_agent_lab/rag/pipeline.py).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-07), which includes learner mechanisms, framework execution, experiments and assertions.

## Evidence sufficiency and faithful reformulation

Retrieval success and answer sufficiency are separate checks. A relevant passage
can omit the requested fact. Abstention is a successful research outcome when the
needed evidence is absent. Preserve the original question, identifiers, negation,
and scope across rewrites. `adaptive_search` accumulates unique evidence and asks
an injected assessor about the original question after every retrieval. The helper
returns a structured trace and leaves answer generation to its caller. The
identifier/scope guard catches obvious drift but requires separate evaluation for
semantic equivalence. Backend failures propagate and do not establish absence.



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](06-planning-and-delegation.md) ? [Next module](08-advanced-evaluations.md)

Estimated time 120 minutes. Difficulty intermediate.

## Retrieval baseline

The master notebook places retrieval before evaluation, context and delegation. Complete
the lexical baseline, learned-vector search, fusion, active-revision hydration and bounded
adaptive retrieval in that section, then continue in the notebook's contents order.
