# Tools and MCP

Adapted from the supplied Northstar course reference. The paired notebook supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

## Tool descriptions influence behavior

A poorly designed tool might look like this:

The model cannot reliably infer what source it searches, how many results are returned, or what a failure looks like.

A better design uses explicit arguments and an unambiguous description:

Now the model sees exactly which search modes are valid.

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
