# Module 6 · Managed deployment

[Course home](course.md) · [Previous module](module-5-capstone.md)

The local assistant has an HTTP interface, an agent runtime, a corpus, a model,
and storage. This module walks through how those responsibilities would be
placed in a managed deployment. The exercise is a deployment design. It uses
the working local capstone as its reference. You will follow one request
through model access, retrieval, human review, and a durable write, then
decide which deployment boundary owns each step.

## 6.1 Understand what the runtime manages

Managed Deep Agents runs the agent harness and Agent Server around a project
definition. The project defines the model, instructions, tools, and skills.
The application still owns which data a user can access and what constitutes
an approved write. For the Northstar brief, there are three distinct records:
the agent thread, the current policy corpus, and the approved brief.
[Managed Deep Agents overview](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview)

| Responsibility | Local course | Managed design |
| --- | --- | --- |
| Run the graph | Deep Agents and LangGraph in FastAPI | Managed runtime and thread API |
| Look up policy | Direct PostgreSQL, OpenSearch and Ollama clients | Reachable retrieval service or connector |
| Choose actions and write | Ollama on your Windows host | Model endpoint reachable from the runtime |
| Keep checkpoints | SQLite | Runtime thread and run storage |
| Store approved briefs | SQLite application table | Durable application store with identity and review |
| Observe execution | Langfuse model, retrieval, and turn spans | Deliberately configured tracing with linked application events |

A managed host sees its own loopback interface. Pointing a hosted process at
`127.0.0.1:11434` cannot reach Ollama on your Windows machine. Likewise, a local
path to a source file is descriptive once that file's contents have been
ingested. Hosted access requires reachable, authenticated endpoints or a
runtime inside the network where those services live.

**Worked placement example.** An internal support team can keep its
PostgreSQL and OpenSearch cluster private. A dedicated retrieval service
authenticates callers and returns only permitted passages. The hosted agent
can reach that service using the organization's approved network route.
The Ollama endpoint needs a route of its own. Receiving search results does
not give the runtime access to the chat model.

## 6.2 Lay out the managed project

```text
northstar-brief/
  agent.py
  instructions.md
  pyproject.toml
  tools/
    search.py
    briefs.py
  skills/
    evidence-brief/
      SKILL.md
```

- **Agent definition.** Configure the chat model and register the retrieval and
  reviewed save tools. The runtime entry point constructs that agent.
- **Instructions and skill.** Keep the role, evidence rules, and retrieved-text
  boundary in project instructions. The skill contains the brief procedure.
- **Retrieval tool.** Return the source ID, excerpt, and exact citation token
  from a service authorized for the user. Keep raw PostgreSQL and OpenSearch
  credentials with the service that actually uses them.
- **Brief tool.** Store reviewed Markdown with a stable operation identity.
  Pass the authenticated reviewer and thread identity to the store.
- **Sandbox.** Add a separate execution environment for document transforms
  when the task needs it. Give it the minimum inputs and dependencies.
- **Channels.** If a chat or service desk supplies requests, map its user
  identity to the application's authorization rules. Display the actual
  proposed action before asking for a decision.

The Academy's managed example shows how to package a configured agent, a
sandbox, a reporting skill, and optional chat integration. In this adaptation,
start with the policy search tool and evidence brief skill, then decide where
you would put the reviewed write. [Academy managed example](https://github.com/langchain-ai/lca-deepagents/tree/9e1fab37b9bcf4d672bdb6b667755f3f668a3fc8/python/m6/dvd_rental_analyst)

## 6.3 Walk through one production request

1. Identify the requesting employee and which policies they can search.
2. Create or open a thread associated with that employee.
3. Retrieve policy within the authorized corpus and generate a draft with
   citations that the employee can resolve.
4. Pause with the proposed write and show its title and content. Only the
   authorized reviewer can resolve the matching interrupt.
5. Commit once and return the brief ID. Record the original request, decision,
   and commit outcome with the run ID or trace ID.
6. Test a second attempt to resolve the same review. It should yield a
   conflict or return the original durable result, according to your API contract.

**Real-world example.** A support organization uses an assistant in a ticketing
system. It retrieves playbooks authorized for the assigned team and proposes
an internal note. A supervisor approves the note and the application writes it
to the ticket. A retried request should never add a duplicate note.

## 6.4 Check failure and retry behavior

| Event | State to preserve | Expected outcome |
| --- | --- | --- |
| Retrieval service is unreachable | Thread and sanitized error type | Report the unavailable search and avoid unsupported claims |
| Reviewer declines | Proposal and review decision | The action creates no committed brief |
| Request is retried after a successful save | Stable operation identity and committed brief ID | The API surfaces the existing result or a conflict |
| User from another team opens the thread ID | Authenticated ownership and corpus permissions | Deny the request at the API boundary |

An operation identity is the value the write service uses to recognize the
same save request on a retry. The local store derives its ID from the thread,
title, and Markdown and ignores exact duplicates. A deployed system should
define what counts as the same operation and use that identity consistently.

## 6.5 Check your deployment design

Sketch the runtime, model endpoint, retrieval service, thread store, and brief
store. For each connection, write down the caller identity, destination, and
data it carries. Start with the local version and compare outcomes for a
normal query, missing evidence, rejected approval, and duplicate request.

**Worked decision.** If inference must stay on this Windows machine and no
approved remote path to Ollama exists, the local FastAPI deployment can meet
that constraint today. A managed runtime becomes an option after the model
endpoint and retrieval service are reachable under their access rules. Keep
the citation and review tests when changing runtimes.
