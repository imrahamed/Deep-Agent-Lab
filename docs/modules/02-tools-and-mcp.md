# Tools and MCP

This chapter develops the Northstar policy research assistant. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 01](01-agent-foundations.md). Recommended next is [Module 03](03-evaluation-foundations.md).

Estimated time 75 minutes. Difficulty introductory. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_foundations_tools.py) alongside the source links below.

## Northstar V2 progression

V1 answers from supplied text. Find the production restore approver without supplied passages. This module adds the capability to search actual policy files and cite exact results.

The deterministic acceptance criterion is a read returns validated evidence and correlated call IDs. Live model judgments are recorded independently.

## Tool descriptions influence behavior

A poorly designed tool leaves its contract ambiguous.

```python
from pathlib import Path
from deep_agent_lab.knowledge import local_search

def do_it(x):
    """Find stuff."""
    return local_search(Path("data/sample"), x)  # No declared argument or outcome contract.
```

Its name and description give the model no reliable source, limit, or outcome contract.

The model cannot reliably infer what source it searches, how many results are returned, or what a failure looks like.

The repository's typed read wrapper makes the contract inspectable and executable.

```python
import asyncio
import json
from pathlib import Path
from deep_agent_lab.knowledge import local_search
from deep_agent_lab.foundations import SearchArgs
from deep_agent_lab.tooling import ToolOutcome, search_read

print(json.dumps(SearchArgs.model_json_schema(), indent=2))
# Strict types, extra fields forbidden, query length 1..4000 with non-whitespace,
# and integer top_k in 1..5. There is no search-mode argument in this schema.

async def search_policy(request: SearchArgs) -> list[dict]:
    """Search the supplied fictional policy corpus, returning at most top_k passages.

    Return an empty list when the search succeeds without matching passages.
    This read cannot approve or save a brief.
    """
    rows = await asyncio.to_thread(local_search, Path("data/sample"), request.query, request.top_k)
    return [row.model_dump() for row in rows]

async def search_tool(arguments: dict, call_id: str) -> ToolOutcome:
    return await search_read(search_policy, arguments, call_id=call_id)

async def examples():
    empty = await search_tool({"query": "ZEPHYR-99"}, "empty-1")
    invalid = await search_tool({"query": "restore", "top_k": 100000}, "invalid-1")
    transient = await search_read(search_policy, {"query": "restore"},
                                  call_id="retry-1", timeout=0.000001, attempts=1)
    assert empty.status == "success" and empty.hits == []
    assert invalid.attempts == 0 and transient.status in {"success", "transient_error"}
    return [empty.model_dump(), invalid.model_dump(), transient.model_dump()]

print(asyncio.run(examples()))
```

Concrete contract objects follow. The short-deadline call above records its actual outcome. A transient failure uses the following status representation.

```json
[
  {"call_id":"empty-1","status":"success","hits":[],"error_code":null,"attempts":1},
  {"call_id":"invalid-1","status":"invalid_request","hits":[],"error_code":"schema","attempts":0},
  {"call_id":"retry-1","status":"transient_error","hits":[],"error_code":"unavailable","attempts":1}
]
```

`permission_denied` and `internal_error` remain distinct statuses. Descriptions
influence model behavior. The trusted caller and production checks authorize actions.

The model can inspect the validated query and result-count limits.

The application can reject invalid requests before consuming backend resources.

## Three outcomes that must remain distinct

**Successful search with zero matches**

The search ran correctly, but no evidence was found. The agent may reformulate its query or report an evidence gap.

**Invalid request**

The model supplied `top_k=100000`, which violates the contract. Reject it without executing retrieval.

**Transient infrastructure failure**

OpenSearch timed out. The absence of results has not been established. Retry within a budget or report retrieval unavailable.

Treating a timeout as "no results" creates a dangerous failure: the agent may confidently claim that a policy does not exist when the search backend was unavailable.

## MCP: Model Context Protocol

MCP standardizes communication between an application and external services exposing tools, resources, or prompts.

It separates three concepts:

- **Host:** The application running the assistant.
- **Client:** The protocol component connecting to a server.
- **Server:** The component exposing capabilities.

The repository's MCP lab already demonstrates a local `FastMCP` server over stdio.

For local development, stdio is often sufficient.

For independently hosted services, an HTTP transport may be appropriate, but it introduces authentication, authorization, server identity, networking, and protocol-version concerns.

**Important:** MCP is a protocol, not a security boundary by itself.

Tool outputs remain untrusted data. A remote server's description cannot authorize actions, and a retrieved document cannot grant itself permission to invoke a write.



## Executable implementation

`asyncio.timeout` bounds an async transport attempt; it cannot forcibly kill arbitrary blocking code. Cancellation propagates rather than becoming a retry. `ToolOutcome` keeps success-with-zero-hits distinct from unavailable retrieval. The MCP lab launches the repository's actual stdio server, discovers its schema, and calls it through ClientSession. Protocol request IDs and the agent's tool-call IDs serve different layers. `remote_mcp_search` uses the installed SDK's real Streamable HTTP client with redirects disabled; OAuth token acquisition belongs to the trusted identity layer. Tool descriptions and returned content grant no permissions.

MCP helps interoperability and process separation. A normal Python function is simpler for an internal tool in the same process. HTTP authentication must validate issuer, audience, expiry and scopes at the server; a bearer header helper does not implement an OAuth server. Remote MCP is optional and requires your own endpoint.

Application sources: [`tooling.py`](../../src/deep_agent_lab/tooling.py), [`mcp_server.py`](../../src/deep_agent_lab/mcp_server.py).

[Open the complete notebook](../../notebooks/02-tools-and-mcp/lab.ipynb), which includes the implementation from scratch, framework execution, failure experiment, assertions and complete exercise solution.



[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](01-agent-foundations.md) ? [Next module](03-evaluation-foundations.md)

Estimated time 75 minutes. Difficulty introductory.
