# Optional extensions after the core course

The reference course identifies these as optional follow-on subjects. They are
not presented as completed integrations in the coverage matrix.

| Extension | Northstar use case | Next evidence required before implementation |
| --- | --- | --- |
| Agent-to-agent protocols | Specialists run in independently deployed services | A concrete interoperability requirement and verified protocol version |
| Browser agents | Policy exists only behind an interactive interface | An authorized browser workflow and a restricted execution environment |
| Multimodal retrieval | Necessary evidence appears in diagrams or scanned sources | Labelled image retrieval tasks and provenance-preserving extraction |
| Prompt optimization | Improve prompts against reliable graders | A representative development set and untouched held-out evaluation |
| Advanced async subagents | Research outlives its parent invocation | Verified pinned APIs and clear ownership, retry and cancellation semantics |
| Knowledge graphs | Traverse explicit relationships across policy entities | Curated entity/relation labels and evidence-backed graph edges |

The core course already implements local specialist delegation, persistent jobs,
text retrieval and controlled ablations. Add one of these extensions only when it
solves an observed failure with a measurable benefit. Browser access, PDF plumbing
and deployment are deliberately secondary to the AI engineering mechanisms.
