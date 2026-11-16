"""Verify the installed API surface used by the course against the lockfile."""

import inspect
import json
import platform
import tomllib
from importlib.metadata import version
from pathlib import Path

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langfuse import Langfuse
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def main():
    root = Path(__file__).resolve().parents[1]
    locked = {
        p["name"]: p["version"] for p in tomllib.loads((root / "uv.lock").read_text())["package"]
    }
    names = [
        "langchain-ollama",
        "deepagents",
        "langchain",
        "langgraph",
        "langgraph-checkpoint-sqlite",
        "mcp",
        "langfuse",
        "nbclient",
        "nbformat",
        "matplotlib",
        "pydantic",
    ]
    installed = {name: version(name) for name in names}
    assert all(installed[name] == locked[name] for name in names)
    assert callable(ChatOllama.invoke)
    assert "schema" in inspect.signature(ChatOllama.with_structured_output).parameters
    assert "tools" in inspect.signature(ChatOllama.bind_tools).parameters
    agent_params = inspect.signature(create_deep_agent).parameters
    assert {
        "model",
        "tools",
        "skills",
        "memory",
        "subagents",
        "permissions",
        "interrupt_on",
        "checkpointer",
        "backend",
        "state_schema",
    } <= agent_params.keys()
    assert "http_client" in inspect.signature(streamable_http_client).parameters
    assert "cursor" in inspect.signature(ClientSession.list_tools).parameters
    assert "span_exporter" in inspect.signature(Langfuse).parameters
    assert callable(Langfuse.start_as_current_observation)
    report = {
        "status": "passed",
        "python": platform.python_version(),
        "versions": installed,
        "lockfile_match": True,
        "deepagents_api": list(agent_params),
        "remote_mcp_client": str(inspect.signature(streamable_http_client)),
    }
    target = root / "docs/reports/compatibility.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
