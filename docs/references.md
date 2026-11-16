# Primary references and dependency compatibility

The executable course uses the repository's locked dependency versions rather
than assuming every feature in current documentation is available. The API surface
was inspected locally and exercised by tests and executed notebooks.
[`compatibility.json`](reports/compatibility.json) records the measured environment.

| Package | Tested version |
| --- | --- |
| Python | 3.11.9 |
| Deep Agents | 0.7.0 |
| LangChain | 1.5.0 |
| LangGraph | 1.2.22 |
| SQLite checkpointer | 3.1.3 |
| MCP Python SDK | 1.30.0 |
| Langfuse | 5.2.0 |
| Pydantic | 2.14.3 |
| nbclient / nbformat | 0.11.0 / 5.11.1 |
| Matplotlib | 3.11.2 |

No framework major upgrade was needed. Matplotlib was added to the optional
notebook dependency group and recorded in `uv.lock`. Run
`python scripts/check_compatibility.py` after any dependency update; it compares
installed versions with the lock and asserts the signatures used by the course.

The verified factory accepts tools, middleware, state schema, backend, permissions,
skills, memory, subagents, interrupts and checkpointer. The MCP remote client uses
`streamable_http_client(..., http_client=...)`; it does not assume an unsupported
headers argument. Langfuse supports the in-memory span-exporter configuration used
by the notebook. A live backend's compatibility is separate from SDK compatibility;
the current official SDK overview describes Python v5's backend requirements.

These are explanatory references, not substitutes for the complete explanations
and executable mechanisms in this repository:

- [Deep Agents 0.7.0 source](https://github.com/langchain-ai/deepagents/tree/deepagents%3D%3D0.7.0): pinned harness implementation.
- [Deep Agents context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering): context sources, offloading and reduction.
- [Deep Agents subagents](https://docs.langchain.com/oss/python/deepagents/subagents): specialist configuration and isolated contexts.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): pause/resume semantics and replay-sensitive operations.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpoints versus cross-thread stores.
- [MCP transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports): stdio and Streamable HTTP.
- [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization): HTTP authorization and token audience requirements.
- [Agent Skills specification](https://agentskills.io/specification): frontmatter, directory structure and progressive disclosure.
- [Langfuse SDK overview](https://langfuse.com/docs/observability/sdk/overview): actual SDK and OpenTelemetry integration.
- [Langfuse masking](https://langfuse.com/docs/observability/features/masking): content classification and redaction.
- [Building effective agents](https://www.anthropic.com/research/building-effective-agents): when workflows and agent loops are appropriate.
- [Effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents): selection and information preservation.
- [Agent evaluation methodology](https://www.anthropic.com/research/demystifying-evals-for-ai-agents): tasks, trials, graders and trajectories.
- [Multi-agent research engineering](https://www.anthropic.com/engineering/multi-agent-research-system): decomposition, independent context and coordination costs.

Northstar policies and source aliases BKP-7 revision 4, INC-3 revision 8 and ACC-2
revision 3 are fictional policy sources. Live ingestion assigns a content
revision digest; the friendly revision number is not the SQL revision key.
