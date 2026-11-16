"""Course experiments using real model calls, tools, middleware and storage."""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.utils import create_file_data
from deepagents.middleware import FilesystemMiddleware
from deepagents.middleware.summarization import create_summarization_middleware
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langsmith import tracing_context
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from deep_agent_lab.instrumentation import ExecutionMetrics
from deep_agent_lab.knowledge import search_knowledge
from deep_agent_lab.model_lab import course_model
from deep_agent_lab.settings import Settings


def input_message(text: str) -> dict:
    return {"messages": [HumanMessage(text)]}


def tool_results(result: dict) -> list[str]:
    return [message.text for message in result["messages"] if isinstance(message, ToolMessage)]


def invoke(agent, prompt: str, config=None) -> dict:
    with tracing_context(enabled=False):
        return agent.invoke(input_message(prompt), config or {"recursion_limit": 16})


async def mcp_lab() -> dict:
    # Inherit configured service variables and .env behavior into the actual MCP server.
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "deep_agent_lab.mcp_server"],
        env={**os.environ, "DEEP_LAB_MODE": "live", "LANGFUSE_ENABLED": "false"},
    )
    with TemporaryFile(mode="w+") as error_log:
        async with stdio_client(params, errlog=error_log) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                result = await client.call_tool("search", {"query": "production restore"})
                if result.isError:
                    raise RuntimeError("Live MCP search failed")
                return {
                    "tools": [item.name for item in tools.tools],
                    "results": [block.text for block in result.content if block.type == "text"],
                }


def workspace_lab() -> dict:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "policy.md").write_text(
            "Reference policies require reviewed changes.", encoding="utf-8"
        )
        backend = CompositeBackend(
            default=StateBackend(),
            routes={"/reference/": FilesystemBackend(root_dir=root, virtual_mode=True)},
        )
        agent = create_deep_agent(
            model=course_model(),
            backend=backend,
            permissions=[
                FilesystemPermission(operations=["write"], paths=["/reference/**"], mode="deny")
            ],
        )
        result = invoke(
            agent,
            "Read /reference/policy.md. Attempt to write a new file at "
            "/reference/alternate.md, inspect the permission result, then write /draft.md.",
        )
        assert not (root / "alternate.md").exists()
        return {
            "results": tool_results(result),
            "host_files": sorted(p.name for p in root.iterdir()),
            "state_files": sorted(result.get("files", {})),
        }


def interpreter_lab() -> dict:
    agent = create_deep_agent(
        model=course_model(), middleware=[CodeInterpreterMiddleware(subagents=False, timeout=2)]
    )
    result = invoke(
        agent,
        "Use the eval JavaScript tool to sum the policy review durations "
        "30, 15 and 45 minutes. Print the numeric result.",
    )
    return {"results": tool_results(result), "answer": result["messages"][-1].text}


def context_lab() -> dict:
    @tool
    def fetch_archive() -> str:
        """Read all repository policy text for inspection."""
        root = Path(__file__).resolve().parents[2] / "data/sample"
        return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.glob("*.md")))

    backend = StateBackend()
    agent = create_deep_agent(
        model=course_model(),
        tools=[fetch_archive],
        backend=backend,
        middleware=[FilesystemMiddleware(backend=backend, tool_token_limit_before_evict=150)],
    )
    result = invoke(agent, "Call fetch_archive once and inspect the resulting archive handle.")
    return {
        "files": sorted(result.get("files", {})),
        "results": tool_results(result),
        "original_chars": len(fetch_archive.invoke({})),
    }


def summarization_lab() -> dict:
    from deep_agent_lab.knowledge import load_policy_evidence

    root = Path(__file__).resolve().parents[2] / "data/sample"
    rows = load_policy_evidence(root)
    backend = StateBackend()
    model = course_model()
    # Force the real summarization middleware to inspect a small configured context.
    summary_model = course_model()
    summary_model.profile = {"max_input_tokens": 1400, "tool_calling": True}
    agent = create_deep_agent(
        model=model,
        backend=backend,
        checkpointer=InMemorySaver(),
        middleware=[create_summarization_middleware(summary_model, backend)],
    )
    notes = [HumanMessage(row.excerpt) for row in rows]
    with tracing_context(enabled=False):
        result = agent.invoke(
            {
                "messages": [
                    *notes,
                    HumanMessage(
                        "Summarize the required "
                        "approval conditions and identify unresolved cross-policy authority."
                    ),
                ]
            },
            {"configurable": {"thread_id": "summary-lab"}, "recursion_limit": 16},
        )
    return {
        "files": sorted(result.get("files", {})),
        "input_messages": len(notes) + 1,
        "checkpoint_messages": len(result["messages"]),
        "answer": result["messages"][-1].text,
    }


def shell_lab() -> dict:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "policy.txt").write_text("Restore approval recorded.", encoding="utf-8")
        command = "type policy.txt" if os.name == "nt" else "cat policy.txt"
        response = LocalShellBackend(root_dir=root, timeout=5).execute(command)
        return {"command": command, "exit_code": response.exit_code, "output": response.output}


def memory_lab() -> dict:
    store = InMemoryStore()
    store.put(("lab", "memory"), "/AGENTS.md", create_file_data("# Format\nUse short bullets."))
    backend = CompositeBackend(
        default=StateBackend(),
        routes={"/memory/": StoreBackend(namespace=lambda _: ("lab", "memory"))},
    )
    agent = create_deep_agent(
        model=course_model(),
        memory=["/memory/AGENTS.md"],
        store=store,
        backend=backend,
        checkpointer=InMemorySaver(),
    )
    results = {}
    for thread in ("A", "B"):
        result = invoke(
            agent,
            f"Read /memory/AGENTS.md. Inspect thread {thread}. "
            + (
                "Write a private note to /private.md."
                if thread == "A"
                else "List files in the workspace and report whether /private.md exists."
            ),
            {"configurable": {"thread_id": thread}, "recursion_limit": 16},
        )
        results[thread] = {
            "tool_results": tool_results(result),
            "files": sorted(result.get("files", {})),
        }
    return results


async def delegation_lab() -> dict:
    settings = Settings(langfuse_enabled=False)

    @tool
    def search_policy(query: str) -> list[dict]:
        """Search actual indexed policy passages with exact citation identifiers."""
        return [row.model_dump() for row in search_knowledge(settings, query, top_k=3)]

    agent = create_deep_agent(
        model=course_model(),
        tools=[search_policy],
        subagents=[
            {
                "name": "policy-researcher",
                "description": "Research one policy topic.",
                "system_prompt": "Search for exact evidence IDs and source quotes.",
                "tools": [search_policy],
                "model": course_model(),
            }
        ],
    )
    metrics = ExecutionMetrics()
    with tracing_context(enabled=False):
        result = await agent.ainvoke(
            input_message(
                "Delegate restore approval and SEV-1 "
                "coordination research to policy-researcher. Verify the returned evidence."
            ),
            {"recursion_limit": 24, "callbacks": [metrics]},
        )
    return {
        "results": tool_results(result),
        "todos": result.get("todos", []),
        "answer": result["messages"][-1].text,
        "steps": [
            call["name"]
            for message in result["messages"]
            if isinstance(message, AIMessage)
            for call in message.tool_calls
        ],
        "metrics": metrics.report(),
    }


def async_lab() -> dict:
    with ThreadPoolExecutor(max_workers=1) as pool:
        model = course_model()
        future = pool.submit(
            model.invoke,
            [
                HumanMessage(
                    "Explain the difference between "
                    "an evidence gap and unavailable retrieval in one sentence."
                )
            ],
        )
        running = future.running()
        return {"worker_running": running, "worker_answer": future.result(timeout=90).text}


LABS = {
    "mcp": mcp_lab,
    "workspace": workspace_lab,
    "interpreter": interpreter_lab,
    "shell": shell_lab,
    "context": context_lab,
    "summarization": summarization_lab,
    "memory": memory_lab,
    "delegation": delegation_lab,
    "async": async_lab,
}


def run_lab(name: str) -> dict:
    from inspect import iscoroutinefunction

    lab = LABS[name]
    return asyncio.run(lab()) if iscoroutinefunction(lab) else lab()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lab", choices=LABS)
    print(json.dumps(run_lab(parser.parse_args().lab), indent=2))
