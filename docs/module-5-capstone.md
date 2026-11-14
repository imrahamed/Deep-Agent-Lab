# Module 5 · Build and operate the research assistant

[Course home](course.md) · [Previous module](module-4-delegation.md) · [Next module](managed-deployment.md)

An on-call lead needs an incident-readiness brief. It should explain who
authorizes a production restore, who responds during a SEV-1, and which rules
cover the overlap. You will ingest the policy documents, inspect the retrieved
evidence, and review the proposed brief before saving it.

Retrieval-augmented generation (RAG) gives a chat model source passages before
it writes. In this project, ingestion makes passages searchable. Retrieval
decides which passages reach the model. Generation turns that evidence into
an answer or draft. These stages can fail independently, so test them in order.

## 5.1 Ingest your corpus

```powershell
uv run deep-lab init
uv run deep-lab doctor
uv run deep-lab ingest data/sample
uv run deep-lab documents
```

`init` verifies that the embedding model returns the configured vector size and
creates the course's search index and PostgreSQL schema. `doctor` checks
PostgreSQL, OpenSearch, both Ollama models and Langfuse authentication when
enabled. `ingest` accepts a Markdown, text, or text-based PDF file, or a directory
of supported files. `documents` should list the backup, access, and incident
response policies after the sample import.

The pipeline loads text, splits it into overlapping character windows, embeds
the chunks with Ollama, and writes searchable records to OpenSearch.
PostgreSQL stores the canonical document and active chunk text. The course
uses the same servers as RAG Lab and owns its own schema and index. The
application opens the service clients directly.

| Stage | Example | How to inspect it |
| --- | --- | --- |
| Load | Read Markdown or extract text page by page from a PDF | Check the file extension and whether text is selectable |
| Chunk | Keep nearby sentences together across a window boundary | Read the returned text and chunk position |
| Embed | Encode a passage with the configured document prefix | Inspect the embedding span's dimensions and vector count |
| Index | Store title, passage and vector for search | Look for the OpenSearch indexing span |
| Activate | Commit the canonical document revision and active chunks | Use `documents` and inspect the PostgreSQL span |

The document ID comes from its source URI. Changing content at the same path
produces a new revision. Re-ingesting unchanged content returns `unchanged`.
If a failed import leaves search candidates without active SQL rows, hydration
filters them out. `reindex` rebuilds chunks from the canonical text and can repair
missing or stale index data. Moving a file changes its source URI.
[Retrieval pipeline](../src/deep_agent_lab/rag/pipeline.py)

### Follow one passage through the pipeline

1. Load the [sample backup policy](../data/sample/backup-policy.md). The file
   contains the approval rule, plus backup timing, retention, and test guidance.
2. Split the text into overlapping passages. Overlap can keep a condition near
   its action when it spans a boundary. Inspect `position` and `text` in search
   results to see the resulting passages. The configured window counts
   characters. Ollama uses tokens internally.
3. Embed each passage with the configured document prefix. At query time the
   same embedding model uses the query prefix. Dimensions describe the length
   of each vector. Matching dimensions alone do not make two different models'
   vectors comparable.
4. Store candidate text and vectors in OpenSearch. Activate the revision and
   its passages in PostgreSQL. On retrieval, the app checks whether the IDs
   returned by the index still correspond to active passages.

For example, if a new import changes the approver, the old paragraph must
stop appearing in new searches. Activating the new revision in SQL determines
which passage IDs are eligible for hydration. Existing agent threads can still
contain earlier excerpts, so start a fresh thread to test a revised policy.

**Practice.** Run the sample import a second time, then compare the statuses.
For a sample of your own, add a short fictional policy under a new path and
ingest just that file. Search for a phrase unique to the policy.

## 5.2 Compare retrieval before running the agent

```powershell
uv run deep-lab search "SEV-1 escalation" --mode keyword --top-k 3
uv run deep-lab search "who coordinates the response after an outage" --mode semantic --top-k 3
uv run deep-lab search "production restore approval" --mode hybrid --top-k 3
```

Keyword search uses BM25 to rank matches to text in the title and passage.
Semantic search embeds the query in the same vector space as the documents
and finds nearby chunks. Hybrid search runs both. Reciprocal rank fusion
combines positions instead of raw scores. With the project's rank constant
of 60, a chunk ranked first by keyword and third by vector gets
`1/61 + 1/63`. A chunk ranked first in only one list gets `1/61`.
The joint match can rank higher even when the score scales differ.

OpenSearch proposes IDs. PostgreSQL hydrates active IDs into the text returned
to callers. A high rank indicates a promising match. You still have to read the
passage and determine whether it supports the claim. `search` is useful for
diagnosing retrieval without involving the chat model.
[OpenSearch client and rank fusion](../src/deep_agent_lab/rag/search.py)

### Interpret a retrieval comparison

For each search mode, note the first result that contains the needed sentence.
A top result about temporary access can contain “approval” but still be
irrelevant to restores. A lower result can contain the entire rule. Start
with `top_k = 3`, then check whether narrower wording moves that passage
up. The score has meaning within its ranking strategy. For the course,
compare whether a relevant chunk appears and where it ranks.

| Observation | Next check |
| --- | --- |
| No matching document is indexed | Run `documents` and ingest the policy if it is absent |
| The right document appears but its chunk lacks the rule | Inspect the excerpt, neighboring positions, and chunk boundaries |
| The direct search finds the rule but the agent uses a different passage | Compare the agent's tool query with the direct query and narrow the prompt if needed |
| The returned passage contains the rule but the answer misstates it | Compare the claim and exact quote. Review the model behavior and the instructions |

## 5.3 Run the application and review an action

```powershell
uv run uvicorn deep_agent_lab.api:app --host 127.0.0.1 --port 8001
```

Open the [local API console](http://127.0.0.1:8001/docs). Try the search endpoint
first, then submit a run. [API walkthrough](operations.md#start-the-api)

| Request | Purpose |
| --- | --- |
| `GET /health` | Check live dependencies |
| `GET /api/v1/documents` | List recent corpus documents |
| `POST /api/v1/search` | Return passages with IDs and scores |
| `POST /api/v1/runs` | Run the agent on a prompt |
| `GET /api/v1/threads/{thread_id}` | Inspect state, evidence, and pending review |
| `POST /api/v1/threads/{thread_id}/review` | Resolve a specific pending action |
| `GET /api/v1/briefs/{brief_id}` | Retrieve approved Markdown |

You can use the CLI for the same review workflow:

```powershell
$thread = "readiness-$([guid]::NewGuid().ToString('N'))"
$prompt = "Draft an evidence brief comparing restore approval and SEV-1 escalation. Search each topic. State what the corpus says about their overlap. Call save_brief to request review."
$proposal = uv run deep-lab ask $prompt --thread $thread | ConvertFrom-Json
$proposal.status
$proposal.steps
$proposal.evidence | Select-Object title, citation
if ($proposal.status -eq 'interrupted') {
    $proposal.reviews[0].action_requests[0].args.markdown
}
```

Live models can choose different tools or stop after drafting. If the status is
`interrupted`, read the Markdown and compare each finding to the supporting
passage. When it is ready, approve the recorded action:

```powershell
$finished = uv run deep-lab review $thread $proposal.reviews[0].id approve |
    ConvertFrom-Json
if ($finished.saved_brief_ids.Count -gt 0) {
    uv run deep-lab brief $finished.saved_brief_ids[0]
}
```

If there is no pending action, inspect `steps` and ask for a short brief with
explicit use of `save_brief`. Check `saved_brief_ids` for a committed brief.
A virtual draft stays in the thread's workspace. The save tool validates citation IDs and records
the commit. The reviewer checks whether those citations support the claims.

**Worked review.** The backup policy names the database operations lead as the
restore approver. The incident policy tells the on-call engineer to page the
incident commander immediately for SEV-1. The sample policies do not specify
joint decision authority. If the draft calls the incident commander a second
restore approver, edit that sentence and retain the correct citations.

## 5.4 Inspect a run in Langfuse

Copy the `trace_id` from a live run and open the project configured by the
referenced Langfuse settings. Follow this chain:

```text
deep-lab.turn
  deep-lab.model
  deep-lab.search
    rag.retrieve
      opensearch.bm25
      ollama.embed.query
      opensearch.knn
      postgres.hydrate
  deep-lab.model
```

The exact calls depend on the selected retrieval mode. A keyword-only retrieval
does not need a query embedding. Compare model durations with retrieval
durations, then look at the number of ranked and hydrated rows. If candidates
are returned but few are hydrated, check that the search index matches the
active corpus. If the right evidence is present and the answer is wrong, focus
on the prompt, model behavior, and review. Ingestion has its own trace ID per
file. Content capture is off in the configured project. Timings, counts, model
names, and reported usage can still be recorded.
[Tracing settings and operations](operations.md#see-the-evidence-and-traces)

## 5.5 Run background research

```powershell
uv run python -m deep_agent_lab.labs async
```

The exercise starts a second graph in a worker. The caller can prepare a brief
outline before collecting the result. Inspect `worker_running`, `supervisor`,
and `worker_answer`. This worker lasts for the Python process. The main
FastAPI assistant invokes its specialists directly within a run.

The Academy's asynchronous pattern uses a separate Agent Server run and task
ID. A supervisor can check progress, send a follow-up, or cancel. For example,
an overnight research job could check migration notes across twenty services.
The chat could return a job ID immediately, then show the report when it is
available. Durable job state needs an owner, input, status, result reference,
timestamps, and a policy for retries. Keep the approved brief write separate
from the background worker so a completed job does not publish automatically.
[Async subagents](https://docs.langchain.com/oss/python/deepagents/async-subagents)

## 5.6 Design an advanced version

A restore drill may include a CSV of timings as well as policy documents.
Retrieve the policy through the normal tool. Give a separate isolated worker
the sanitized measurements, compute totals and check for missing values, then
return aggregates and source references. The parent brings the two outputs
together and presents the proposed report for review.

This design combines the execution boundary from Module 2 with the background
lifecycle above. A chart alone cannot establish whether the drill met the
policy. The reviewer needs the measured start and end times, the policy's
target, and any gaps such as a missing validation timestamp. In this course,
the isolated worker and durable background queue are design extensions.

## Acceptance cases

| Case | What to check |
| --- | --- |
| Restore approval | Backup policy is in the evidence and the answer names the operations lead |
| Two-topic comparison | Backup and incident passages support the corresponding claims |
| Cross-check direct search and agent evidence | At least one agent excerpt supports the same approval rule found in direct search |
| Joint authority | The brief identifies the missing procedure |
| Pending save | The proposal is visible and the brief has no committed ID yet |
| Edited approval | Fetch by saved ID and compare with the reviewed replacement |
| Rejection | No brief ID is returned for that action |
| Unknown citation | An edited proposal with a fabricated token produces no save |
| Repeat ingest | Unchanged source files are skipped |

### Worked acceptance example

A short brief for the bundled corpus could contain these findings. Copy the
citation tokens from your run beside the corresponding sentences.

- The database operations lead approves production restores.
- In a SEV-1, the on-call engineer immediately pages the incident commander.
- **Evidence gap.** The supplied policies do not establish who resolves a
  disagreement between these roles. Check the incident command or disaster
  recovery runbook before assigning joint decision authority.

Use this as a claim-level comparison. The model can change the order and
wording. Check which sources support the substantive claims, review the
proposal, and retrieve the approved Markdown using `saved_brief_ids`.
