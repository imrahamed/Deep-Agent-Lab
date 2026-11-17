# Security

This chapter develops the Northstar policy research assistant. The master notebook section supplies executable implementations and checks. Examples using BKP-7, INC-3 and ACC-2 are conceptual source aliases; the executable application uses its stored IDs and exact citation tokens.

Prerequisites include [Module 02](02-tools-and-mcp.md) and [Module 08](08-advanced-evaluations.md). Recommended next is [Module 10](10-human-review.md).

Estimated time 90 minutes. Difficulty advanced. Consult the [glossary](../glossary.md) for unfamiliar terms.

Inspect the [module contract tests](../../tests/test_review_jobs_security.py) alongside the source links below.

## Why prompt injection occurs

LLMs process instructions and data through a shared context representation.

Applications distinguish these categories through message roles, tool boundaries, and other protocol mechanisms, but the model can still be influenced by adversarial text inside lower-trust content.

The vulnerable flow looks like this:

A secure design does not rely on asking the model to ignore malicious text.

It prevents untrusted content from independently obtaining authority.

## Separate data from authority

Northstar should distinguish these layers:

| Layer                 | Trust assumption                                        |
| --------------------- | ------------------------------------------------------- |
| Application code      | Enforces authorization and invariants                   |
| Trusted configuration | Defines permitted workflow behavior                     |
| User request          | Expresses user intent within granted permissions        |
| Retrieved policy      | Supplies domain evidence, not executable instructions   |
| Specialist response   | Supplies proposed findings, not independent authority   |
| MCP response          | Supplies tool data; trust depends on server and content |
| Model output          | Proposal requiring validation before action             |

A model may request an action, but application code decides whether it is permitted.

For example, `save_brief` must not execute unless the current authenticated principal has permission and the exact action has been approved.

## Authentication versus authorization

Authentication identifies the caller.

Authorization determines what that caller may access or modify.

Suppose the API accepts:

```
GET /api/v1/threads/alices-thread
```

Knowing the thread ID must not grant access to its contents.

The repository's current API is a local learning service without authentication. A multi-user extension requires an identity model and ownership checks.

The principal must come from the validated authentication context.

It must not be constructed from a `user_id` parameter selected by the model.

The implemented capstone requires the exact tenant and owner for thread access. It deliberately grants no team-wide thread bypass. Team and project membership are checked separately for scoped memory.

## Filesystem and execution boundaries

Your existing repository already routes reference files through a read-only filesystem and provides controlled execution demonstrations.

This is a strong starting point.

When adding broader capabilities, distinguish a **virtual workspace** from unrestricted host filesystem access.

A Northstar researcher generally needs to read policy references and write temporary draft files. It does not need access to application credentials, arbitrary host paths, or general-purpose shell commands.

Avoid exposing a broad `execute_command(command: str)` tool when the task only requires calculations or read-only search.

If code execution is necessary, use a constrained execution environment with explicit filesystem, network, resource, and process permissions.

Path restrictions must account for traversal and symlinks, not just a string-prefix comparison.

## Secret exposure through traces

Observability tools can accidentally collect credentials, personally identifiable information, and confidential policy data.

Your repository already defaults to suppressing content capture in its Langfuse instrumentation and tests that behavior.

Extend that principle to metadata, exception messages, HTTP headers, tool arguments, and saved artifacts.

A safe trace might contain:

```
{
  "operation": "search_knowledge",
  "status": "success",
  "result_count": 4,
  "duration_ms": 230,
  "query_hash": "redacted-or-hashed-value"
}
```

A risky trace could contain a complete database connection string, bearer token, or an entire private support ticket.

Tracing libraries do not eliminate the need for application-level data classification and redaction.

## MCP-specific concerns

Remote MCP connections introduce additional attack surfaces.

The application must verify the remote server's identity and authorization requirements, limit the permissions granted to it, and avoid forwarding credentials to unintended endpoints.

Tool names and descriptions supplied by an untrusted MCP server must not be treated as higher-priority instructions.

The MCP specification explicitly treats tool execution as sensitive and describes consent, user control, data privacy, and authorization responsibilities.



## Executable implementation

The test sends adversarial content through the real search tool and graph. The actual model response is retained, while the enforced interrupt and exact-action save boundary protect persistence. Authentication identifies the caller. Authorization checks the authenticated tenant, owner and permission before accessing a checkpoint. The original HTTP API remains a local single-user lab; the Northstar wrapper adds trusted caller scope. `Path.resolve` prevents traversal and follows existing symlinks, but an attacker who can concurrently replace workspace links requires OS-level isolation.

Prompt instructions and text filters are useful guidance but do not enforce authorization. Keep dangerous execution tools out of the research agent. Restrict telemetry by data classification: content suppression alone does not sanitize arbitrary metadata.

Application sources: [`security.py`](../../src/deep_agent_lab/security.py), [`capstone.py`](../../src/deep_agent_lab/capstone.py), [`agent.py`](../../src/deep_agent_lab/agent.py).

[Open this master notebook section](../../notebooks/deep_agents.ipynb#module-09), which includes learner mechanisms, framework execution, experiments and assertions.


[Start here](../start-here.md) ? [Course order](../course.md) ? [Glossary](../glossary.md) ? [Previous module](08-advanced-evaluations.md) ? [Next module](10-human-review.md)

Estimated time 90 minutes. Difficulty advanced.
