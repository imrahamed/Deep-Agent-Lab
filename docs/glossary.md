# Glossary

| Term | Meaning in Northstar |
| --- | --- |
| Agent | A model-driven feedback loop that chooses actions from observations |
| Harness | Instructions, tools, skills, context handling and execution support around a model |
| Runtime | The system that executes and coordinates graph steps; LangGraph here |
| Workflow | Application-defined control flow, such as the bounded research preflight |
| Inference | Computing a model response from tokenized input |
| Token | A model-specific unit of encoded text, not necessarily a word |
| Structured output | A response constrained to a schema; structure does not prove truth |
| Tool call | A model proposal to invoke a capability, identified by a call ID |
| Tool result | An application-produced observation correlated with a tool call |
| MCP | Protocol connecting an agent host's clients with tool/resource/prompt servers |
| Context window | The bounded model-visible input and generation allocation |
| Offloading | Keeping bulky originals outside active context with a retrievable pointer |
| Compaction | Reducing narrative history while preserving required structured state |
| Prompt caching | Provider-side reuse of eligible prompt computation; not persistent knowledge |
| Skill | A discoverable reusable procedure with metadata and optional supporting files |
| Memory | Intentionally reusable information scoped to authorized interactions |
| Checkpoint | Persistent graph execution state for a thread |
| Provenance | The source identity, revision and exact evidence behind a finding |
| BM25 | Lexical ranking using term rarity, frequency saturation and length normalization |
| Embedding | A vector representation generated in a particular model's coordinate space |
| Cosine similarity | Directional similarity of nonzero vectors in the same space |
| RRF | Reciprocal rank fusion, combining ranking positions rather than raw scores |
| Reranker | A second-stage relevance scorer over a smaller candidate set |
| Claim support | Whether cited evidence actually establishes the claim |
| Abstention | Explicitly withholding an unsupported factual assertion |
| Model judge | A model prediction assessing output according to a rubric |
| Calibration | Comparing judge predictions with human-reviewed labels |
| Ablation | Removing one capability while controlling other experimental conditions |
| Trajectory | Observable tool/model action sequence, distinct from the final answer |
| Prompt injection | Lower-trust content attempting to acquire instruction authority |
| Authentication | Establishing caller identity |
| Authorization | Checking what that authenticated caller may access or change |
| Exact-action review | Approval bound to the precise operation, payload, scope and version |
| Idempotency | Repeating a logical operation converges on the same effect |
| Lease | Time-limited ownership of a job attempt |
| Fencing | Rejecting stale workers using a current ownership token at the protected boundary |
| Durable job | Persistent input, lifecycle, ownership, attempt and result metadata |
| Reconciliation | Inspecting committed state to resolve an ambiguous operation outcome |
| Span | A timed unit of observable work with optional parent context |
| Trace | Related spans sharing an execution identity |
| Lineage | Durable links from the approved brief to its action, job, evidence and trace |

See the [learning path](course.md) for executable examples of these terms.
