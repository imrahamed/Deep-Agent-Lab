# Run Deep Agent Lab

[Setup](../README.md) · [Course map](course.md) · [Live capstone](module-5-capstone.md)

## Configuration

This checkout's ignored `.env` sets `DEEP_LAB_MODE=live` and contains its own
PostgreSQL, OpenSearch, Ollama and Langfuse configuration. It does not depend on
another repository's environment file. On a new machine, copy `.env.example`
and supply the service endpoints and credentials directly.
From highest to lowest precedence, the CLI mode flag overrides the
process environment, then the local `.env`, inherited settings, and defaults.

| Setting | What it controls |
| --- | --- |
| `RAG_LAB_ENV_FILE` | Optional shared configuration source; unused by this checkout |
| `POSTGRES_DSN` | Database connection. The course uses schema `deep_agent_lab` |
| `OPENSEARCH_URL`, `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD` | Search endpoint and basic authentication when configured |
| `OPENSEARCH_INDEX` | Course index, initially `deep-agent-lab-v1` |
| `OLLAMA_URL`, `OLLAMA_CHAT_MODEL` | Local endpoint and model used for tool calls and answers |
| `OLLAMA_EMBED_MODEL`, `EMBEDDING_DIMENSIONS` | Model and vector size used for search |
| `LANGFUSE_ENABLED`, `LANGFUSE_CAPTURE_CONTENT` | Whether to export observations and include prompt or response content |
| `DEEP_LAB_STATE_DIR` | Base for local checkpoints and approved briefs, with separate `demo` and `live` subdirectories |

This checkout has Langfuse enabled and content capture off. Use
`uv run deep-lab ask "<question>"` for actual model and retrieval execution. Use the same mode
for subsequent `thread`, `review`, and `brief` commands so they read the same
state directory. The API takes its mode from configuration.

## Initialize and maintain the corpus

Run from the project root:

```powershell
uv run deep-lab init
uv run deep-lab doctor
uv run deep-lab ingest data/sample
uv run deep-lab documents
uv run deep-lab search "production restore approval" --mode hybrid --top-k 3
```

- **Initialize.** Check the embedding shape and create the course schema,
  tables, and index. The configured role needs permission to create them.
- **Ingest.** Accepts Markdown, UTF-8 text, and PDFs with extractable text.
  Pass a file or folder. An unchanged source is skipped. Use `--force` to
  rebuild a specific input.
- **Inspect.** `documents` shows recent documents. `search` returns hits with
  their `chunk_id`, `source`, `position`, `score`, and `text`.
- **Reindex.** Run `uv run deep-lab reindex` to rebuild the configured index
  from PostgreSQL. If the embedding model or prefixes change, choose a new
  index name beginning with `deep-agent-lab-`, check the new dimensions,
  initialize the index, and reindex before using it for searches.

Yellow cluster health allows searching when primary shards are available.
A mapping-profile mismatch calls for checking the configured model,
dimensions, and prefixes. [Ingestion and search lesson](module-5-capstone.md#51-ingest-your-corpus)

## Start the API

```powershell
uv run uvicorn deep_agent_lab.api:app --host 127.0.0.1 --port 8001
```

Open the [interactive API](http://127.0.0.1:8001/docs). For the local service,
set `$env:DEEP_LAB_MODE = 'live'` in that terminal before starting it. Use
`Remove-Item Env:DEEP_LAB_MODE` to return to the checkout setting. The lab is a
single-worker loopback service with no user authentication. Keep thread writes
sequential across CLI and API processes.

| Endpoint | Request and result |
| --- | --- |
| `GET /health` | Dependency status in the configured mode |
| `GET /api/v1/documents` | Recently indexed documents in live mode |
| `POST /api/v1/search` | `query`, optional `mode` and `top_k`. Returns ranked passages in live mode |
| `POST /api/v1/runs` | `prompt` and optional `thread_id`. Returns an answer or pending review |
| `GET /api/v1/threads/{thread_id}` | Latest checkpoint summary, with evidence and pending actions |
| `POST /api/v1/threads/{thread_id}/review` | `interrupt_id` and ordered `decisions`. Resumes the matching action |
| `GET /api/v1/briefs/{brief_id}` | Approved Markdown and its creation record |

### Find evidence and submit a brief

```powershell
$api = 'http://127.0.0.1:8001'
$search = @{
    query = 'production restore approval'
    mode = 'hybrid'
    top_k = 3
} | ConvertTo-Json
Invoke-RestMethod "$api/api/v1/search" -Method Post -ContentType 'application/json' -Body $search

$body = @{
    prompt = 'Draft and save a short evidence brief about production restore approval. Use save_brief to request review.'
} | ConvertTo-Json
$run = Invoke-RestMethod "$api/api/v1/runs" -Method Post -ContentType 'application/json' -Body $body
$run.status
if ($run.status -eq 'interrupted') {
    $run.reviews[0].action_requests[0].args
}
```

The search above requires live mode. The run request works in either mode.
When the run is `interrupted`, compare the proposed Markdown with the returned
evidence before resolving it. Run the approval block only for an interrupted run. If the live model stops
without requesting a save, inspect `steps` and ask for a shorter proposal that calls `save_brief`.

```powershell
$review = @{
    interrupt_id = $run.reviews[0].id
    decisions = @(@{type = 'approve'})
} | ConvertTo-Json -Depth 4
$reviewUrl = "$api/api/v1/threads/$($run.thread_id)/review"
$finished = Invoke-RestMethod $reviewUrl -Method Post -ContentType 'application/json' -Body $review

if ($finished.saved_brief_ids.Count -gt 0) {
    Invoke-RestMethod "$api/api/v1/briefs/$($finished.saved_brief_ids[0])"
}
```

For a changed proposal, send a decision with `type = 'edit'`, `title`, and
`markdown`. For a declined proposal, send `type = 'reject'`. Supply one
decision per requested action in request order. Invalid citations can cause an
approved or edited action to finish without a brief ID.

## See the evidence and traces

| Field | How to read it |
| --- | --- |
| `status` | `interrupted` waits for a decision. `completed` means the graph finished the turn |
| `evidence` | Passages seen in the thread, along with exact citation tokens |
| `unknown_citations` | Tokens in the final answer absent from the thread evidence |
| `steps` and `todos` | Tool call history and current plan. Inspect tool results for proof of what happened |
| `saved_brief_ids` | IDs committed during that turn. Fetch the brief to verify the exact stored text |
| `trace_id` | Langfuse trace for the invocation when tracing is active |

`doctor` checks Langfuse authentication. Open the configured project and look up
the trace ID returned by the agent or ingestion command. Inspect the root and
child observations for durations, error types, model usage, and result counts.
With content capture off, application observations omit prompt and answer text.
SQLite checkpoints still hold local prompts, working drafts, evidence, and tool
results. [Read a trace](module-5-capstone.md#54-inspect-a-run-in-langfuse)

## Troubleshoot by symptom

| Symptom | Check |
| --- | --- |
| `doctor` reports a missing table or index | Run `init` in live mode and check the configured resource names |
| Ollama reports a missing model | Compare `ollama list` with both configured model names |
| Search misses the expected policy | Run `documents`, then search for a distinctive phrase in keyword mode |
| The model answers without a citation | Check that `search_knowledge` ran and that the right excerpt was returned |
| A new prompt or review returns 409 | Inspect the thread and use the current review ID in the same mode |
| An agent returns no saved ID | Check for a pending review, rejected action, or citation validation failure |
| A run times out or reaches its step limit | Try a smaller request and inspect whether the model repeats tool calls |

The API uses 404 for an absent thread or brief and 422 for invalid request data
or a graph step limit. An unavailable dependency can surface as an API error
or as a retrieval failure in the agent's answer.

## Verification

```powershell
uv sync --locked --extra dev --extra notebook
uv run --extra dev ruff check src tests scripts
uv run --extra dev pytest
uv run --extra notebook python scripts/check_notebook.py
uv run deep-lab doctor
```
