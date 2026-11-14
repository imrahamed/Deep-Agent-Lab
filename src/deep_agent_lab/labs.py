"""Small reproducible experiments for the public course modules."""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from threading import Event

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.utils import create_file_data
from deepagents.middleware import FilesystemMiddleware
from deepagents.middleware.summarization import create_summarization_middleware
from langchain.agents.middleware import TodoListMiddleware
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_quickjs import CodeInterpreterMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class Replay(FakeMessagesListChatModel):
    """Use scripted model replies so the real middleware behavior is reproducible."""

    profile: dict = {"max_input_tokens": 16384, "tool_calling": True}

    def bind_tools(self, tools, **kwargs):
        return self


def call(name: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": name, "name": name, "args": args}])


def input_message(text: str) -> dict:
    return {"messages": [HumanMessage(text)]}


def tool_results(result: dict) -> list[str]:
    return [msg.text for msg in result["messages"] if isinstance(msg, ToolMessage)]


async def mcp_lab() -> dict:
    with TemporaryFile(mode="w+") as errlog:
        return await _mcp_exchange(errlog)


async def _mcp_exchange(errlog) -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "deep_agent_lab.mcp_server"],
        env={"DEEP_LAB_MODE": "demo", "PYTHONIOENCODING": "utf-8"},
    )
    # A Windows child needs a real stderr handle when the caller is a Jupyter kernel.
    async with (
        stdio_client(params, errlog=errlog) as (reader, writer),
        ClientSession(reader, writer) as client,
    ):
        await client.initialize()
        tools = await client.list_tools()
        response = await client.call_tool("search", {"query": "production restore"})
        assert not response.isError

        @tool
        async def mcp_search(query: str) -> str:
            """Search the sample corpus via the initialized MCP session."""
            result = await client.call_tool("search", {"query": query})
            if result.isError:
                raise RuntimeError("MCP search failed")
            return json.dumps(
                result.structuredContent
                or [block.text for block in result.content if block.type == "text"]
            )

        agent = create_deep_agent(
            model=Replay(
                responses=[
                    call("mcp_search", query="production restore"),
                    AIMessage(content="Read the evidence in the tool response."),
                ]
            ),
            tools=[mcp_search],
        )
        result = await agent.ainvoke(input_message("Find the restore rule."))
        return {"tools": [item.name for item in tools.tools], "results": tool_results(result)}


def workspace_lab() -> dict:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "policy.md").write_text("Original policy.", encoding="utf-8")
        backend = CompositeBackend(
            default=StateBackend(),
            routes={"/reference/": FilesystemBackend(root_dir=root, virtual_mode=True)},
        )
        agent = create_deep_agent(
            model=Replay(
                responses=[
                    call("read_file", file_path="/reference/policy.md"),
                    call("write_file", file_path="/reference/alternate.md", content="Unauthorized"),
                    call("write_file", file_path="/draft.md", content="A working draft."),
                    call("read_file", file_path="/draft.md"),
                    AIMessage(content="Finished."),
                ]
            ),
            backend=backend,
            permissions=[
                FilesystemPermission(operations=["write"], paths=["/reference/**"], mode="deny"),
            ],
        )
        result = agent.invoke(input_message("Compare routing and permissions."))
        return {
            "results": tool_results(result),
            "host_files": sorted(item.name for item in root.iterdir()),
            "state_files": sorted(result["files"]),
        }


def interpreter_lab() -> dict:
    agent = create_deep_agent(
        model=Replay(
            responses=[
                call("eval", code="console.log([30, 15, 45].reduce((a, b) => a + b, 0));"),
                AIMessage(content="Finished."),
            ]
        ),
        middleware=[CodeInterpreterMiddleware(subagents=False, timeout=2)],
    )
    result = agent.invoke(input_message("Total the three durations."))
    return {"results": tool_results(result)}


def context_lab() -> dict:
    @tool
    def fetch_archive() -> str:
        """Return a deliberately large operations archive."""
        return "The archive records a simulated restore drill. " * 200

    model = Replay(
        responses=[
            call("fetch_archive"),
            AIMessage(content="The archive was written to virtual storage."),
        ]
    )
    backend = StateBackend()
    agent = create_deep_agent(
        model=model,
        tools=[fetch_archive],
        backend=backend,
        middleware=[FilesystemMiddleware(backend=backend, tool_token_limit_before_evict=150)],
    )
    result = agent.invoke(input_message("Fetch the archive."))
    return {
        "tool_message": tool_results(result)[0][:600],
        "files": sorted(result["files"]),
        "original_chars": len(fetch_archive.invoke({})),
    }


def summarization_lab() -> dict:
    summary_model = Replay(
        responses=[AIMessage(content="The previous notes describe restore testing.")]
    )
    summary_model.profile = {"max_input_tokens": 1400, "tool_calling": True}
    model = Replay(responses=[AIMessage(content="I can use the summary and retained prompt.")])
    backend = StateBackend()
    saver = InMemorySaver()
    agent = create_deep_agent(
        model=model,
        backend=backend,
        checkpointer=saver,
        middleware=[create_summarization_middleware(summary_model, backend)],
    )
    config = {"configurable": {"thread_id": "summary-lab"}}
    notes = []
    for n in range(6):
        notes.extend(
            [
                HumanMessage(f"Drill {n}: " + "Restore testing note. " * 150),
                AIMessage(content="Recorded."),
            ]
        )
    result = agent.invoke(
        {
            "messages": [*notes, HumanMessage("Summarize restore testing.")],
        },
        config,
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
        backend = LocalShellBackend(root_dir=root, timeout=5)
        response = backend.execute(command)
        return {"command": command, "exit_code": response.exit_code, "output": response.output}


def memory_lab() -> dict:
    store = InMemoryStore()
    store.put(
        ("lab", "memory"), "/AGENTS.md", create_file_data("# Brief format\nUse short bullets.")
    )
    checkpointer = InMemorySaver()
    backend = CompositeBackend(
        default=StateBackend(),
        routes={"/memory/": StoreBackend(namespace=lambda _: ("lab", "memory"))},
    )
    agent = create_deep_agent(
        model=Replay(
            responses=[
                call("read_file", file_path="/memory/AGENTS.md"),
                call("write_file", file_path="/private.md", content="Only in A."),
                AIMessage(content="Finished A."),
                call("read_file", file_path="/memory/AGENTS.md"),
                call("ls", path="/"),
                AIMessage(content="Finished B."),
            ]
        ),
        memory=["/memory/AGENTS.md"],
        store=store,
        backend=backend,
        checkpointer=checkpointer,
    )
    results = {}
    for thread in ("A", "B"):
        result = agent.invoke(
            input_message(f"Inspect thread {thread}."),
            {"configurable": {"thread_id": thread}},
        )
        results[thread] = {
            "tool_results": tool_results(result),
            "files": sorted(result.get("files", {})),
        }
    return results


def specialist(topic: str, response: str) -> dict:
    return {
        "name": topic,
        "description": f"Review the {topic} operations policy.",
        "system_prompt": f"Report the most relevant requirement for {topic}.",
        "model": Replay(responses=[AIMessage(content=response)]),
        "tools": [],
    }


async def delegation_lab() -> dict:
    # In an Ollama run the model can construct this batch from a variable-length input.
    batch = """
const topics = ["restore", "incident"];
const results = await Promise.all(
  topics.map(topic => task({subagentType: topic, description: "Review " + topic}))
);
console.log(JSON.stringify(results));
"""
    agent = create_deep_agent(
        model=Replay(
            responses=[
                call(
                    "write_todos",
                    todos=[{"content": "Review both topics", "status": "in_progress"}],
                ),
                call("eval", code=batch),
                call(
                    "write_todos", todos=[{"content": "Review both topics", "status": "completed"}]
                ),
                AIMessage(content="Finished both reviews."),
            ]
        ),
        middleware=[TodoListMiddleware(), CodeInterpreterMiddleware(max_subagent_concurrency=2)],
        subagents=[
            specialist("restore", "The database operations lead approves restores."),
            specialist("incident", "The incident commander coordinates the response."),
        ],
    )
    result = await agent.ainvoke(input_message("Review the restore and incident policies."))
    return {"results": tool_results(result), "todos": result["todos"]}


def async_lab() -> dict:
    """Show launch, status and result delivery with a local worker and real agent graph."""
    entered = Event()
    release = Event()

    def run_worker() -> str:
        entered.set()
        if not release.wait(5):
            raise TimeoutError("The supervisor did not release the demo worker")
        agent = create_deep_agent(
            model=Replay(
                responses=[
                    AIMessage(
                        content="The database operations lead approves a production restore."
                    ),
                ]
            )
        )
        return agent.invoke(input_message("Find the restore approver."))["messages"][-1].text

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_worker)
        try:
            if not entered.wait(5):
                raise TimeoutError("The demo worker did not start")
            running = future.running()
            supervisor = "The brief outline is ready while research runs."
        finally:
            release.set()
        return {
            "worker_running": running,
            "supervisor": supervisor,
            "worker_answer": future.result(),
        }


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
